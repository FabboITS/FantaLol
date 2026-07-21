package com.fantalol.backend.league;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class RosterPolicy {
    private final FantaTeamRepository fantaTeamRepository;

    public Limits forLeague(League league) {
        int teamCount = league.getParticipantCount() != null
                ? league.getParticipantCount()
                : Math.toIntExact(fantaTeamRepository.countByLeagueId(league.getId()));
        return teamCount <= 5 ? new Limits(10, 2) : new Limits(5, 1);
    }

    public record Limits(int maxRosterSize, int maxPerRole) {}
}
