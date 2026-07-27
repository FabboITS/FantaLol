package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;
import org.springframework.stereotype.Component;

@Component
public class GameScoreCalculator {
    public double calculate(PlayerRole role, int kills, int deaths, int assists, int cs, boolean win) {
        return weightedTotal(role, kills, deaths, assists, cs) + (win ? 3.0 : 0.0);
    }

    public double calculateAverage(
            PlayerRole role,
            int kills,
            int deaths,
            int assists,
            int cs,
            int wins,
            int gamesPlayed
    ) {
        if (gamesPlayed <= 0) {
            return 0.0;
        }
        return (weightedTotal(role, kills, deaths, assists, cs) + wins * 3.0) / gamesPlayed;
    }

    private double weightedTotal(PlayerRole role, int kills, int deaths, int assists, int cs) {
        RoleScoreWeights.Weights weights = RoleScoreWeights.forRole(role);
        return kills * weights.kills()
                + assists * weights.assists()
                - deaths * weights.deaths()
                + (cs / 100.0) * weights.csPerHundred();
    }
}
