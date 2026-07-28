package com.fantalol.backend.matchday;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.lineup.EffectiveLineupService;
import com.fantalol.backend.lineup.LineupWindow;
import com.fantalol.backend.matchday.dto.FormationRequest;
import com.fantalol.backend.matchday.dto.FormationResponse;
import com.fantalol.backend.matchday.dto.LineupWindowResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.time.Clock;

/**
 * Gestisce la formazione (titolari + capitano) che ogni FantaTeam schiera per una giornata.
 */
@Service
@RequiredArgsConstructor
public class FormationService {

    private static final int NUMERO_TITOLARI = 5;

    private final FormationRepository formationRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final MatchdayRepository matchdayRepository;
    private final PlayerStatRepository playerStatRepository;
    private final UserService userService;
    private final EffectiveLineupService effectiveLineupService;
    private final LineupWindow lineupWindow;
    private final Clock clock;

    @Transactional(readOnly = true)
    public FormationResponse findByTeamAndMatchday(Long fantaTeamId, Long matchdayId) {
        Formation formation = formationRepository.findByFantaTeamIdAndMatchdayId(fantaTeamId, matchdayId)
                .orElseThrow(() -> new ResourceNotFoundException("Nessuna formazione trovata per la squadra e la giornata indicate"));
        return formationResponse(formation, java.util.Map.of());
    }

    @Transactional(readOnly = true)
    public List<FormationResponse> findHistory(Long fantaTeamId) {
        return formationRepository.findByFantaTeamId(fantaTeamId).stream()
                .sorted(java.util.Comparator.comparing(formation -> formation.getMatchday().getNumero()))
                .map(formation -> {
                    java.util.Map<Long, Double> scores = formation.getTitolari().stream().collect(
                            java.util.stream.Collectors.toMap(LecPlayer::getId, player -> playerStatRepository
                                    .findByMatchdayIdAndLecPlayerId(formation.getMatchday().getId(), player.getId())
                                    .map(PlayerStat::getFantavoto).orElse(0.0)));
                    return formationResponse(formation, scores);
                }).toList();
    }

    @Transactional(readOnly = true)
    public LineupWindowResponse lineupWindow(String username, Long fantaTeamId) {
        FantaTeam fantaTeam = fantaTeamRepository.findById(fantaTeamId)
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata con id: " + fantaTeamId));
        verifyCanManage(username, fantaTeam);
        LineupWindow.Status status = lineupWindow.status(clock.instant());
        boolean fixedRoster = fantaTeam.getLeague().getParticipantCount() != null
                && fantaTeam.getLeague().getParticipantCount() >= 6;
        return new LineupWindowResponse(status.editable() && !fixedRoster,
                status.nextEffectiveAt(), status.reason());
    }

    @Transactional
    Formation resolveEffectiveFormation(FantaTeam fantaTeam, Matchday matchday) {
        Optional<Formation> existing = formationRepository.findByFantaTeamIdAndMatchdayId(
                fantaTeam.getId(), matchday.getId());
        if (existing.isPresent()) {
            return existing.get();
        }

        Formation.FormationBuilder builder = Formation.builder().fantaTeam(fantaTeam).matchday(matchday);
        Integer participants = fantaTeam.getLeague().getParticipantCount();
        if (participants != null && participants >= 6) {
            Set<LecPlayer> players = rosterEntryRepository.findByFantaTeamId(fantaTeam.getId()).stream()
                    .map(entry -> entry.getLecPlayer())
                    .collect(java.util.stream.Collectors.toSet());
            if (players.size() != NUMERO_TITOLARI
                    || players.stream().map(LecPlayer::getRuolo).distinct().count() != NUMERO_TITOLARI) {
                throw new BusinessRuleException("La rosa deve contenere esattamente un player per ruolo");
            }
            return formationRepository.save(builder.titolari(players).source(FormationSource.AUTOMATIC).build());
        }

        Optional<Formation> previous = formationRepository
                .findFirstByFantaTeamIdAndMatchdayNumeroLessThanAndSourceOrderByMatchdayNumeroDesc(
                        fantaTeam.getId(), matchday.getNumero(), FormationSource.SUBMITTED);
        if (previous.isPresent()) {
            return formationRepository.save(builder
                    .titolari(new HashSet<>(previous.get().getTitolari()))
                    .source(FormationSource.CARRIED)
                    .build());
        }
        return formationRepository.save(builder.source(FormationSource.MISSING).build());
    }

    /**
     * Imposta (o sovrascrive) la formazione di una FantaTeam per una giornata.
     * Regole di business:
     * <ul>
     *     <li>solo il proprietario della squadra può schierare la formazione</li>
     *     <li>devono essere schierati esattamente {@value #NUMERO_TITOLARI} titolari, uno per ruolo</li>
     *     <li>tutti i titolari devono appartenere alla rosa acquistata all'asta dalla squadra</li>
     *     <li>il capitano (opzionale) deve essere uno dei titolari schierati</li>
     * </ul>
     */
    @Transactional
    public FormationResponse impostaFormazione(String username, Long fantaTeamId, FormationRequest request) {
        FantaTeam fantaTeam = fantaTeamRepository.findById(fantaTeamId)
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata con id: " + fantaTeamId));

        verifyCanManage(username, fantaTeam);

        var matchday = matchdayRepository.findById(request.matchdayId())
                .orElseThrow(() -> new ResourceNotFoundException("Giornata non trovata con id: " + request.matchdayId()));

        if (matchday.isChiusa()) {
            throw new BusinessRuleException("La giornata " + matchday.getNumero() + " è chiusa: non puoi modificare la formazione");
        }
        if (fantaTeam.getLeague().isAuctionOpen()) {
            throw new BusinessRuleException("Termina l'asta prima di modificare la formazione");
        }
        if (fantaTeam.getLeague().getParticipantCount() != null
                && fantaTeam.getLeague().getParticipantCount() >= 6) {
            throw new BusinessRuleException("Nelle leghe con almeno 6 squadre la formazione coincide automaticamente con la rosa");
        }

        List<Long> titolariIds = request.titolariIds();
        if (titolariIds.size() != NUMERO_TITOLARI || new HashSet<>(titolariIds).size() != NUMERO_TITOLARI) {
            throw new BusinessRuleException("Devi schierare esattamente " + NUMERO_TITOLARI + " titolari diversi");
        }

        Set<LecPlayer> titolari = new HashSet<>();
        for (Long playerId : titolariIds) {
            if (!rosterEntryRepository.existsByFantaTeamIdAndLecPlayerId(fantaTeamId, playerId)) {
                throw new BusinessRuleException("Il player con id " + playerId + " non appartiene alla rosa di questa squadra");
            }
            LecPlayer player = lecPlayerRepository.findById(playerId)
                    .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + playerId));
            titolari.add(player);
        }

        if (titolari.stream().map(LecPlayer::getRuolo).distinct().count() != NUMERO_TITOLARI) {
            throw new BusinessRuleException("La formazione deve contenere un player per ruolo: TOP, JUNGLE, MID, ADC e SUPPORT");
        }

        Formation formation = formationRepository.findByFantaTeamIdAndMatchdayId(fantaTeamId, request.matchdayId())
                .orElse(Formation.builder().fantaTeam(fantaTeam).matchday(matchday).build());

        formation.setTitolari(titolari);
        formation.setSource(FormationSource.SUBMITTED);

        Formation saved = formationRepository.save(formation);
        effectiveLineupService.schedule(username, fantaTeamId, titolari);
        return formationResponse(saved, java.util.Map.of());
    }

    private FormationResponse formationResponse(Formation formation, java.util.Map<Long, Double> scores) {
        LineupWindow.Status status = lineupWindow.status(clock.instant());
        boolean fixedRoster = formation.getFantaTeam().getLeague().getParticipantCount() != null
                && formation.getFantaTeam().getLeague().getParticipantCount() >= 6;
        List<LecPlayer> effectivePlayers = Optional.ofNullable(
                        effectiveLineupService.activePlayersAt(formation.getFantaTeam().getId(), clock.instant()))
                .orElseGet(Set::of).stream().toList();
        return FormationResponse.from(formation, scores, status.editable() && !fixedRoster,
                status.nextEffectiveAt(), effectivePlayers);
    }

    private void verifyCanManage(String username, FantaTeam fantaTeam) {
        if (!fantaTeam.getOwner().getUsername().equals(username)
                && userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN) {
            throw new BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica");
        }
    }
}
