package com.fantalol.backend.lineup;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.integration.lec.LecSyncProperties;
import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.matchday.FormationSource;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Optional;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class LineupBackfillService {

    public static final Instant BACKFILL_FROM = Instant.parse("2026-07-23T22:00:00Z");

    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final FormationRepository formationRepository;
    private final EffectiveLineupPeriodRepository periodRepository;
    private final EffectiveLineupService effectiveLineupService;
    private final LecSyncProperties lecSyncProperties;

    @Transactional
    public void backfill() {
        for (FantaTeam fantaTeam : fantaTeamRepository.findAll()) {
            if (periodRepository.existsByFantaTeamId(fantaTeam.getId())) {
                continue;
            }
            playersToBackfill(fantaTeam).ifPresent(players ->
                    effectiveLineupService.createBackfillPeriods(
                            fantaTeam, players, lecSyncProperties.backfillFrom().toInstant()));
        }
    }

    private Optional<Set<LecPlayer>> playersToBackfill(FantaTeam fantaTeam) {
        Integer participants = fantaTeam.getLeague().getParticipantCount();
        if (participants != null && participants >= 6) {
            Set<LecPlayer> players = rosterEntryRepository.findByFantaTeamId(fantaTeam.getId()).stream()
                    .map(entry -> entry.getLecPlayer())
                    .collect(java.util.stream.Collectors.toSet());
            return isValidLineup(players) ? Optional.of(players) : Optional.empty();
        }
        return formationRepository.findByFantaTeamIdOrderByMatchdayNumeroDesc(fantaTeam.getId()).stream()
                .filter(this::isValidSubmittedFormation)
                .map(Formation::getTitolari)
                .findFirst();
    }

    private boolean isValidSubmittedFormation(Formation formation) {
        if (formation.getSource() != FormationSource.SUBMITTED && formation.getSource() != FormationSource.CARRIED) {
            return false;
        }
        return isValidLineup(formation.getTitolari());
    }

    private boolean isValidLineup(Set<LecPlayer> players) {
        if (players == null || players.size() != PlayerRole.values().length
                || players.stream().map(LecPlayer::getId).distinct().count() != PlayerRole.values().length) {
            return false;
        }
        Set<PlayerRole> roles = players.stream().map(LecPlayer::getRuolo)
                .collect(java.util.stream.Collectors.toSet());
        return roles.equals(java.util.EnumSet.allOf(PlayerRole.class));
    }
}
