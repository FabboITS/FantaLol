package com.fantalol.backend.lineup;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.team.LecPlayer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.ZonedDateTime;
import java.util.Optional;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class LineupBackfillService {

    public static final Instant BACKFILL_FROM = ZonedDateTime.of(2026, 7, 24, 0, 0, 0, 0, LineupWindow.ZONE).toInstant();

    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final FormationRepository formationRepository;
    private final EffectiveLineupPeriodRepository periodRepository;
    private final EffectiveLineupService effectiveLineupService;

    @Transactional
    public void backfill() {
        for (FantaTeam fantaTeam : fantaTeamRepository.findAll()) {
            if (periodRepository.existsByFantaTeamId(fantaTeam.getId())) {
                continue;
            }
            playersToBackfill(fantaTeam).ifPresent(players ->
                    effectiveLineupService.createBackfillPeriods(fantaTeam, players, BACKFILL_FROM));
        }
    }

    private Optional<Set<LecPlayer>> playersToBackfill(FantaTeam fantaTeam) {
        Integer participants = fantaTeam.getLeague().getParticipantCount();
        if (participants != null && participants >= 6) {
            return Optional.of(rosterEntryRepository.findByFantaTeamId(fantaTeam.getId()).stream()
                    .map(entry -> entry.getLecPlayer())
                    .collect(java.util.stream.Collectors.toSet()));
        }
        return formationRepository.findFirstByFantaTeamIdOrderByMatchdayNumeroDesc(fantaTeam.getId())
                .map(Formation::getTitolari);
    }
}
