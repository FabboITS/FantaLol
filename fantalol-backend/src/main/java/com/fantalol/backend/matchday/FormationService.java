package com.fantalol.backend.matchday;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.matchday.dto.FormationRequest;
import com.fantalol.backend.matchday.dto.FormationResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

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

    @Autowired(required = false)
    private com.fantalol.backend.scoring.MatchdayScoringEngine scoringEngine;

    @Transactional(readOnly = true)
    public FormationResponse findByTeamAndMatchday(Long fantaTeamId, Long matchdayId) {
        Formation formation = formationRepository.findByFantaTeamIdAndMatchdayId(fantaTeamId, matchdayId)
                .orElseThrow(() -> new ResourceNotFoundException("Nessuna formazione trovata per la squadra e la giornata indicate"));
        return FormationResponse.from(formation);
    }

    @Transactional(readOnly = true)
    public List<FormationResponse> findHistory(Long fantaTeamId) {
        return formationRepository.findByFantaTeamId(fantaTeamId).stream()
                .sorted(java.util.Comparator.comparing(formation -> formation.getMatchday().getNumero()))
                .map(formation -> {
                    java.util.Map<Long, Double> scores = formation.getTitolari().stream().collect(
                            java.util.stream.Collectors.toMap(LecPlayer::getId, player ->
                                    formation.getFormulaVersion() != null && scoringEngine != null
                                            ? scoringEngine.playerMatchdayScore(formation.getMatchday().getId(), player.getId())
                                            : playerStatRepository
                                            .findByMatchdayIdAndLecPlayerId(formation.getMatchday().getId(), player.getId())
                                            .map(PlayerStat::getFantavoto).orElse(0.0)));
                    return FormationResponse.from(formation, scores);
                }).toList();
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

    /** Materializes automatic, carried or missing formations before live scoring starts. */
    @Transactional
    public void ensureEffectiveFormations(Matchday matchday) {
        if (matchday.getLeague().isAuctionOpen()) return;
        fantaTeamRepository.findByLeagueId(matchday.getLeague().getId())
                .forEach(team -> resolveEffectiveFormation(team, matchday));
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

        if (!fantaTeam.getOwner().getUsername().equals(username)
                && userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN) {
            throw new BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica");
        }

        var matchday = matchdayRepository.findById(request.matchdayId())
                .orElseThrow(() -> new ResourceNotFoundException("Giornata non trovata con id: " + request.matchdayId()));

        if (matchday.isChiusa()) {
            throw new BusinessRuleException("La giornata " + matchday.getNumero() + " è chiusa: non puoi modificare la formazione");
        }
        if (matchday.isFormationLocked()) {
            throw new BusinessRuleException("Le formazioni della giornata sono bloccate");
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
        if (scoringEngine != null && scoringEngine.usesGameScoring(matchday.getId())) {
            scoringEngine.recomputeMatchday(matchday.getId());
        }
        return FormationResponse.from(saved);
    }
}
