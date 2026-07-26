package com.fantalol.backend.scoring;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class PlayerGameStatTest {

    @Test
    void equalOracleAndManualCandidatesAreAutomaticallyVerified() {
        PlayerGameStat stat = new PlayerGameStat();

        stat.submit(StatSource.MANUAL, 2, 1, 7, 240, true, "admin");
        stat.submit(StatSource.ORACLE, 2, 1, 7, 240, true, "oracle-sync");

        assertThat(stat.isConflict()).isFalse();
        assertThat(stat.getEffectiveSource()).isEqualTo(StatSource.ORACLE);
        assertThat(stat.effectiveKills()).isEqualTo(2);
    }

    @Test
    void disagreementKeepsThePreviousValueUntilAnAdminResolvesIt() {
        PlayerGameStat stat = new PlayerGameStat();
        stat.submit(StatSource.MANUAL, 2, 1, 7, 240, true, "admin");

        stat.submit(StatSource.ORACLE, 3, 1, 7, 241, true, "oracle-sync");

        assertThat(stat.isConflict()).isTrue();
        assertThat(stat.getEffectiveSource()).isEqualTo(StatSource.MANUAL);
        assertThat(stat.effectiveKills()).isEqualTo(2);

        stat.resolve(StatSource.ORACLE);

        assertThat(stat.isConflict()).isFalse();
        assertThat(stat.getEffectiveSource()).isEqualTo(StatSource.ORACLE);
        assertThat(stat.effectiveKills()).isEqualTo(3);
    }

    @Test
    void changingEitherCandidateReopensAResolvedConflict() {
        PlayerGameStat stat = new PlayerGameStat();
        stat.submit(StatSource.MANUAL, 2, 1, 7, 240, true, "admin");
        stat.submit(StatSource.ORACLE, 3, 1, 7, 241, true, "oracle-sync");
        stat.resolve(StatSource.MANUAL);

        stat.submit(StatSource.ORACLE, 4, 1, 7, 241, true, "oracle-sync");

        assertThat(stat.isConflict()).isTrue();
        assertThat(stat.getEffectiveSource()).isEqualTo(StatSource.MANUAL);
    }
}
