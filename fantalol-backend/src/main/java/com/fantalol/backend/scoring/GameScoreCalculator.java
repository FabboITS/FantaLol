package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;
import org.springframework.stereotype.Component;

@Component
public class GameScoreCalculator {
    public double calculate(
            PlayerRole role,
            int kills,
            int deaths,
            int assists,
            int cs,
            int visionScore,
            boolean win
    ) {
        return weightedTotal(role, kills, deaths, assists, cs, visionScore) + (win ? 3.0 : 0.0);
    }

    public double calculateAverage(
            PlayerRole role,
            int kills,
            int deaths,
            int assists,
            int cs,
            int visionScore,
            int wins,
            int gamesPlayed
    ) {
        if (gamesPlayed <= 0) {
            return 0.0;
        }
        return (weightedTotal(role, kills, deaths, assists, cs, visionScore) + wins * 3.0) / gamesPlayed;
    }

    private double weightedTotal(
            PlayerRole role,
            int kills,
            int deaths,
            int assists,
            int cs,
            int visionScore
    ) {
        RoleScoreWeights.Weights weights = RoleScoreWeights.forRole(role);
        return kills * weights.kills()
                + assists * weights.assists()
                - deaths * weights.deaths()
                + resourceScore(role, cs, visionScore, weights);
    }

    private double resourceScore(
            PlayerRole role,
            int cs,
            int visionScore,
            RoleScoreWeights.Weights weights
    ) {
        if (role == PlayerRole.SUPPORT) {
            return visionScore / 50.0;
        }
        return (cs / 100.0) * weights.csPerHundred();
    }
}
