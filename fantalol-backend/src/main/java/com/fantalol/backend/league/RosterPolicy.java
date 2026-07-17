package com.fantalol.backend.league;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class RosterPolicy {
    private final FantaTeamRepository fantaTeamRepository;

    public Limits forLeague(League league) {
        long teamCount = fantaTeamRepository.countByLeagueId(league.getId());
        return teamCount == 10 ? new Limits(5, 1) : new Limits(10, 2);
    }

    public record Limits(int maxRosterSize, int maxPerRole) {}
}
