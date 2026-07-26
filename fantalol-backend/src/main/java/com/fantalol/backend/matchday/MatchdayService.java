package com.fantalol.backend.matchday;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.League;
import com.fantalol.backend.league.LeagueService;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.matchday.dto.MatchdayRequest;
import com.fantalol.backend.matchday.dto.MatchdayResponse;
import com.fantalol.backend.matchday.dto.PlayerStatRequest;
import com.fantalol.backend.matchday.dto.PlayerStatResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Instant;
import java.util.List;

/**
 * Gestisce le giornate di campionato e l'inserimento (da parte dell'ADMIN) delle
 * statistiche reali dei player, da cui viene derivato automaticamente il fantavoto.
 */
@Service
@RequiredArgsConstructor
public class MatchdayService {

    private final MatchdayRepository matchdayRepository;
    private final PlayerStatRepository playerStatRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final FantaScoreCalculator fantaScoreCalculator;
    private final FormationRepository formationRepository;
    private final FormationService formationService;
    private final FantaTeamRepository fantaTeamRepository;
    private final LeagueService leagueService;
    private final UserService userService;

    @Autowired(required = false)
    private com.fantalol.backend.scoring.MatchdayLockAuditRepository lockAuditRepository;

    @Autowired(required = false)
    private com.fantalol.backend.scoring.MatchdayScoringEngine scoringEngine;

    @Transactional(readOnly = true)
    public List<MatchdayResponse> findAll() {
        return matchdayRepository.findAll().stream().map(this::response).toList();
    }

    @Transactional(readOnly = true)
    public MatchdayResponse findById(Long id) {
        return response(getOrThrow(id));
    }

    @Transactional
    public MatchdayResponse create(String username, MatchdayRequest request) {
        League league = leagueService.getOrThrow(request.leagueId());
        assertLeagueAdmin(username, league);
        if (matchdayRepository.existsByLeagueIdAndStatus(league.getId(), MatchdayStatus.OPEN)) {
            throw new BusinessRuleException("Esiste già una giornata aperta per questa lega");
        }
        if (matchdayRepository.findByLeagueIdAndNumero(league.getId(), request.numero()).isPresent()) {
            throw new BusinessRuleException("Esiste già una giornata con numero: " + request.numero());
        }
        league = leagueService.startCompetitionAndOpenAuction(league);
        Matchday matchday = Matchday.builder()
                .league(league)
                .numero(request.numero())
                .descrizione(request.descrizione())
                .data(request.data())
                .build();
        return MatchdayResponse.from(matchdayRepository.save(matchday));
    }

    @Transactional(readOnly = true)
    public List<PlayerStatResponse> findStats(Long matchdayId) {
        return playerStatRepository.findByMatchdayId(matchdayId).stream().map(PlayerStatResponse::from).toList();
    }

    /**
     * Inserisce (o aggiorna) le statistiche di un player per una giornata e ne calcola
     * automaticamente il fantavoto tramite {@link FantaScoreCalculator}.
     */
    @Transactional
    public PlayerStatResponse inserisciStatistiche(String username, Long matchdayId, PlayerStatRequest request) {
        Matchday matchday = getOrThrow(matchdayId);
        assertGlobalAdmin(username);
        assertAuctionClosed(matchday);
        if (matchday.isChiusa()) {
            throw new BusinessRuleException("La giornata " + matchday.getNumero() + " è già chiusa: impossibile modificare le statistiche");
        }

        LecPlayer player = lecPlayerRepository.findById(request.lecPlayerId())
                .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + request.lecPlayerId()));

        PlayerStat stat = playerStatRepository.findByMatchdayIdAndLecPlayerId(matchdayId, player.getId())
                .orElse(PlayerStat.builder().matchday(matchday).lecPlayer(player).build());

        stat.setKills(request.kills() != null ? request.kills() : 0);
        stat.setMorti(request.morti() != null ? request.morti() : 0);
        stat.setAssist(request.assist() != null ? request.assist() : 0);
        stat.setCs(request.cs() != null ? request.cs() : 0);
        stat.setVittoria(request.vittoria());
        stat.setWins(request.vittoria() ? 1 : 0);
        stat.setFantavoto(fantaScoreCalculator.calcola(stat));

        return PlayerStatResponse.from(playerStatRepository.save(stat));
    }

    /** Chiude la giornata e calcola i risultati con la formula associata alla giornata. */
    @Transactional
    public MatchdayResponse chiudiGiornata(String username, Long matchdayId) {
        Matchday matchday = getOrThrow(matchdayId);
        assertLeagueAdmin(username, matchday.getLeague());
        assertAuctionClosed(matchday);
        if (matchday.isChiusa()) {
            throw new BusinessRuleException("La giornata " + matchday.getNumero() + " è già chiusa");
        }

        var teams = fantaTeamRepository.findByLeagueId(matchday.getLeague().getId());
        if (scoringEngine != null && scoringEngine.usesGameScoring(matchdayId)) {
            for (var team : teams) {
                formationService.resolveEffectiveFormation(team, matchday);
            }
            scoringEngine.recomputeMatchday(matchdayId);
            matchday.setChiusa(true);
            matchday.setStatus(MatchdayStatus.CLOSED);
            return response(matchdayRepository.save(matchday));
        }

        List<Formation> formazioni = new java.util.ArrayList<>();
        for (var team : teams) {
            Formation formazione = formationService.resolveEffectiveFormation(team, matchday);
            double totale = 0.0;
            for (var titolare : formazione.getTitolari()) {
                double fantavoto = playerStatRepository.findByMatchdayIdAndLecPlayerId(matchdayId, titolare.getId())
                        .map(PlayerStat::getFantavoto)
                        .orElse(0.0);
                totale += fantavoto;
            }
            double media = formazione.getSource() == FormationSource.MISSING ? 0.0 : totale / 5.0;
            formazione.setPunteggioTotale(media);
            team.setPunti((team.getPunti() != null ? team.getPunti() : 0.0) + media);
            formazioni.add(formazione);
        }
        formationRepository.saveAll(formazioni);
        fantaTeamRepository.saveAll(teams);

        matchday.setChiusa(true);
        matchday.setStatus(MatchdayStatus.CLOSED);
        return MatchdayResponse.from(matchdayRepository.save(matchday));
    }

    @Transactional
    public MatchdayResponse markWaitingForPostponedMatches(String username, Long matchdayId) {
        Matchday matchday = getOrThrow(matchdayId);
        assertLeagueAdmin(username, matchday.getLeague());
        assertAuctionClosed(matchday);
        if (matchday.isChiusa()) {
            throw new BusinessRuleException("A closed matchday cannot be moved back to waiting");
        }
        matchday.setStatus(MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES);
        return MatchdayResponse.from(matchdayRepository.save(matchday));
    }

    @Transactional
    public MatchdayResponse setFormationLocked(String username, Long matchdayId, boolean locked) {
        Matchday matchday = getOrThrow(matchdayId);
        assertLeagueParticipant(username, matchday.getLeague());
        matchday.setFormationLocked(locked);
        matchday.setFormationLockedAt(Instant.now());
        matchday.setFormationLockedBy(username);
        Matchday saved = matchdayRepository.save(matchday);
        if (lockAuditRepository != null) {
            lockAuditRepository.save(com.fantalol.backend.scoring.MatchdayLockAudit.builder()
                    .matchday(saved).locked(locked).actor(username).build());
        }
        return response(saved);
    }

    Matchday getOrThrow(Long id) {
        return matchdayRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Giornata non trovata con id: " + id));
    }

    private void assertLeagueAdmin(String username, League league) {
        User user = userService.findByUsernameOrThrow(username);
        if (user.getRole() != Role.ADMIN && !league.getAdmin().getUsername().equals(username)) {
            throw new BusinessRuleException("Solo l'admin della lega può gestire questa giornata");
        }
    }

    private void assertGlobalAdmin(String username) {
        if (userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN) {
            throw new BusinessRuleException("Solo l'amministratore globale può inserire le statistiche");
        }
    }

    private void assertAuctionClosed(Matchday matchday) {
        if (matchday.getLeague().isAuctionOpen()) {
            throw new BusinessRuleException("Termina l'asta prima di usare o chiudere la giornata");
        }
    }

    private void assertLeagueParticipant(String username, League league) {
        User user = userService.findByUsernameOrThrow(username);
        boolean participant = fantaTeamRepository.findByLeagueIdAndOwnerUsername(league.getId(), username).isPresent();
        if (user.getRole() != Role.ADMIN && !league.getAdmin().getUsername().equals(username) && !participant) {
            throw new BusinessRuleException("Solo i partecipanti della lega possono bloccare o sbloccare la giornata");
        }
    }

    private MatchdayResponse response(Matchday matchday) {
        MatchdayResponse response = MatchdayResponse.from(matchday);
        return scoringEngine == null || !scoringEngine.usesGameScoring(matchday.getId()) ? response
                : response.withScoringStatus(scoringEngine.status(matchday.getId()).name());
    }
}
