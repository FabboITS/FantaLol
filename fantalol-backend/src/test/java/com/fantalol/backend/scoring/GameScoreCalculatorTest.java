package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

class GameScoreCalculatorTest {
    private final GameScoreCalculator calculator = new GameScoreCalculator();

    @Test
    void appliesTheApprovedSummer2026WeightsForEveryRole() {
        assertThat(calculator.calculate(PlayerRole.TOP, 1, 1, 1, 100, 0, true)).isEqualTo(7.25);
        assertThat(calculator.calculate(PlayerRole.JUNGLE, 1, 1, 1, 100, 0, true)).isEqualTo(6.95);
        assertThat(calculator.calculate(PlayerRole.MID, 1, 1, 1, 100, 0, true)).isEqualTo(7.0);
        assertThat(calculator.calculate(PlayerRole.ADC, 1, 1, 1, 100, 0, true)).isEqualTo(6.85);
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 1, 1, 1, 100, 50, true))
                .isCloseTo(6.95, within(0.0001));
    }

    @Test
    void scoresPartialHundredsOfCsContinuously() {
        assertThat(calculator.calculate(PlayerRole.TOP, 0, 0, 0, 50, 999, false)).isEqualTo(0.625);
        assertThat(calculator.calculate(PlayerRole.ADC, 0, 0, 0, 125, 999, false)).isEqualTo(1.375);
    }

    @Test
    void scoresSupportVisionContinuouslyAndIgnoresSupportCs() {
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 0, 0, 999, 0, false)).isZero();
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 0, 0, 0, 25, false)).isEqualTo(0.5);
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 0, 0, 0, 50, false)).isEqualTo(1.0);
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 0, 0, 0, 100, false)).isEqualTo(2.0);
    }

    @Test
    void preservesNegativeScores() {
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 4, 0, 0, 0, false)).isEqualTo(-7.0);
    }

    @Test
    void averagesAggregatedStatisticsAcrossPlayedGames() {
        assertThat(calculator.calculateAverage(
                PlayerRole.MID, 4, 2, 8, 400, 0, 2, 2
        )).isEqualTo(17.0);
    }
}
