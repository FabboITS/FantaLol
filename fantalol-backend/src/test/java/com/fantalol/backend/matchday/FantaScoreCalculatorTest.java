package com.fantalol.backend.matchday;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.scoring.ScoringFormulaVersion;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

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

    @Test
    void usesTheSummer2026RoleFormulaForPlayerStats() {
        LecPlayer support = LecPlayer.builder().ruolo(PlayerRole.SUPPORT).build();
        PlayerStat stat = PlayerStat.builder()
                .lecPlayer(support)
                .kills(1)
                .morti(1)
                .assist(1)
                .cs(100)
                .wins(1)
                .build();

        assertThat(calculator.calculate(stat)).isCloseTo(6.15, within(0.0001));
    }

    @Test
    void preservesTheHistoricalFormulaForVersionedStats() {
        LecPlayer support = LecPlayer.builder().ruolo(PlayerRole.SUPPORT).build();
        PlayerStat stat = PlayerStat.builder()
                .lecPlayer(support)
                .kills(1)
                .morti(1)
                .assist(1)
                .cs(100)
                .wins(1)
                .gamesPlayed(1)
                .formulaVersion(ScoringFormulaVersion.HISTORICAL)
                .build();

        assertThat(calculator.calculate(stat)).isEqualTo(7.0);
    }
}
