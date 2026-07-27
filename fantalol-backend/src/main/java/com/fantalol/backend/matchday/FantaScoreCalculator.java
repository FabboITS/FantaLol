package com.fantalol.backend.matchday;

import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.scoring.ScoringFormulaVersion;
import org.springframework.stereotype.Component;

/** Calculates the official fantasy score described in Rules.md. */
@Component
public class FantaScoreCalculator {
    private final GameScoreCalculator summer2026Calculator = new GameScoreCalculator();

    public double calculate(int kills, int deaths, int assists, int cs, int wins) {
        return kills * 3.0
                + assists * 2.0
                - deaths * 2.0
                + Math.floorDiv(cs, 100)
                + wins * 3.0;
    }

    public double calculate(PlayerStat stat) {
        if (stat.getFormulaVersion() == ScoringFormulaVersion.HISTORICAL) {
            return calculate(stat.getKills(), stat.getMorti(), stat.getAssist(), stat.getCs(), stat.getWins());
        }
        return summer2026Calculator.calculateAverage(
                stat.getLecPlayer().getRuolo(),
                stat.getKills(),
                stat.getMorti(),
                stat.getAssist(),
                stat.getCs(),
                stat.getWins(),
                stat.getGamesPlayed()
        );
    }

    /** Kept for source compatibility with the existing Italian service methods. */
    public double calcola(int kills, int morti, int assist, int cs, boolean vittoria) {
        return calculate(kills, morti, assist, cs, vittoria ? 1 : 0);
    }

    public double calcola(PlayerStat stat) {
        return calculate(stat);
    }
}
