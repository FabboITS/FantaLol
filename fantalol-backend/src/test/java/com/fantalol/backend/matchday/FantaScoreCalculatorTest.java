package com.fantalol.backend.matchday;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

class FantaScoreCalculatorTest {

    private final FantaScoreCalculator calculator = new FantaScoreCalculator();

    @Test
    void calcolaFantavotoBaseSenzaBonusNeMalus() {
        double fantavoto = calculator.calcola(6.0, 0, 0, 0, false, false);
        assertThat(fantavoto).isEqualTo(6.0);
    }

    @Test
    void aggiungeBonusPerKillEAssist() {
        // 6.0 + 3 kill * 0.5 + 2 assist * 0.3 = 6.0 + 1.5 + 0.6 = 8.1
        double fantavoto = calculator.calcola(6.0, 3, 0, 2, false, false);
        assertThat(fantavoto).isCloseTo(8.1, within(0.001));
    }

    @Test
    void sottraeMalusPerMorti() {
        // 6.0 - 2 morti * 0.4 = 5.2
        double fantavoto = calculator.calcola(6.0, 0, 2, 0, false, false);
        assertThat(fantavoto).isCloseTo(5.2, within(0.001));
    }

    @Test
    void aggiungeBonusMvpEVittoria() {
        // 6.0 + 2.0 (mvp) + 1.0 (vittoria) = 9.0
        double fantavoto = calculator.calcola(6.0, 0, 0, 0, true, true);
        assertThat(fantavoto).isCloseTo(9.0, within(0.001));
    }

    @Test
    void ilFantavotoNonPuoScendereSottoZero() {
        double fantavoto = calculator.calcola(1.0, 0, 20, 0, false, false);
        assertThat(fantavoto).isEqualTo(0.0);
    }

    @ParameterizedTest
    @CsvSource({
            "6.0, 5, 0, 0, false, false, 8.5",
            "6.0, 0, 0, 10, false, false, 9.0",
            "6.5, 1, 1, 1, true, false, 8.9"
    })
    void calcolaVariCasiCombinati(double votoBase, int kills, int morti, int assist,
                                   boolean mvp, boolean vittoria, double atteso) {
        double fantavoto = calculator.calcola(votoBase, kills, morti, assist, mvp, vittoria);
        assertThat(fantavoto).isCloseTo(atteso, within(0.001));
    }
}
