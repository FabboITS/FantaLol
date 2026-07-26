package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class GameScoreCalculatorTest {
    private final GameScoreCalculator calculator = new GameScoreCalculator();

    @Test
    void usesContinuousCsInsteadOfDiscardingPartialHundreds() {
        assertThat(calculator.calculate(PlayerRole.MID, 0, 0, 0, 50, false))
                .isEqualTo(0.5);
        assertThat(calculator.calculate(PlayerRole.ADC, 0, 0, 0, 125, false))
                .isEqualTo(1.5);
    }

    @Test
    void appliesTheFrozenWeightsForEveryRole() {
        assertThat(calculator.calculate(PlayerRole.TOP, 1, 1, 1, 100, true)).isEqualTo(7.1);
        assertThat(calculator.calculate(PlayerRole.JUNGLE, 1, 1, 1, 100, true)).isEqualTo(6.95);
        assertThat(calculator.calculate(PlayerRole.MID, 1, 1, 1, 100, true)).isEqualTo(7.0);
        assertThat(calculator.calculate(PlayerRole.ADC, 1, 1, 1, 100, true)).isEqualTo(7.2);
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 1, 1, 1, 100, true)).isEqualTo(6.2);
    }

    @Test
    void preservesNegativeScores() {
        assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 4, 0, 0, false))
                .isEqualTo(-8.0);
    }
}
