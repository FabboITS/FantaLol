package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;
import org.springframework.stereotype.Component;

@Component
public class GameScoreCalculator {
    public double calculate(PlayerRole role, int kills, int deaths, int assists, int cs, boolean win) {
        RoleScoreWeights.Weights weights = RoleScoreWeights.forRole(role);
        return kills * weights.kills()
                + assists * weights.assists()
                - deaths * weights.deaths()
                + (cs / 100.0) * weights.csPerHundred()
                + (win ? 3.0 : 0.0);
    }

    public double calculate(PlayerGameStat stat) {
        return calculate(stat.getPlayer().getRuolo(), stat.effectiveKills(), stat.effectiveDeaths(),
                stat.effectiveAssists(), stat.effectiveCs(), stat.effectiveWin());
    }
}
