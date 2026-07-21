package com.fantalol.backend.matchday;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class FantaScoreCalculatorTest {
    private final FantaScoreCalculator calculator = new FantaScoreCalculator();

    @Test
    void appliesKillsAssistsDeathsCompleteHundredsOfCsAndWin() {
        assertThat(calculator.calcola(2, 1, 3, 250, true)).isEqualTo(15.0);
    }

    @Test
    void allowsNegativeScores() {
        assertThat(calculator.calcola(0, 4, 0, 99, false)).isEqualTo(-8.0);
    }

    @Test
    void awardsCsOnlyForCompleteHundreds() {
        assertThat(calculator.calcola(0, 0, 0, 99, false)).isZero();
        assertThat(calculator.calcola(0, 0, 0, 100, false)).isEqualTo(1.0);
        assertThat(calculator.calcola(0, 0, 0, 199, false)).isEqualTo(1.0);
        assertThat(calculator.calcola(0, 0, 0, 200, false)).isEqualTo(2.0);
    }
}
