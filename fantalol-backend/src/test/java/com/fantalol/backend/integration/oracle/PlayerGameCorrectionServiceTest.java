package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.integration.oracle.dto.ManualPlayerGameCorrectionRequest;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import jakarta.validation.Validation;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class PlayerGameCorrectionServiceTest {
    private static final Instant NOW = Instant.parse("2026-07-28T13:30:00Z");

    private final ProviderPlayerGameStatRepository repository = mock(ProviderPlayerGameStatRepository.class);
    private final ProviderPlayerGameStat stat = ProviderPlayerGameStat.builder()
            .id(9L)
            .providerGame(ProviderGame.builder().id(4L).externalGameId("GAME-1").build())
            .lecPlayer(LecPlayer.builder().id(7L).nickname("Caps").ruolo(PlayerRole.MID).build())
            .sourceRole(PlayerRole.MID)
            .rawParticipated(true)
            .rawKills(4)
            .rawDeaths(2)
            .rawAssists(6)
            .rawCs(250)
            .rawVisionScore(20)
            .rawWin(true)
            .fantasyScore(25.0)
            .overridden(false)
            .build();
    private PlayerGameCorrectionService service;

    @BeforeEach
    void setUp() {
        when(repository.findByProviderGameExternalGameIdAndLecPlayerId("GAME-1", 7L))
                .thenReturn(Optional.of(stat));
        when(repository.save(stat)).thenReturn(stat);
        service = new PlayerGameCorrectionService(
                repository,
                new GameScoreCalculator(),
                Clock.fixed(NOW, ZoneOffset.UTC));
    }

    @Test
    void suppliedValuesBecomeACompleteAuditedOverrideWithoutChangingProviderValues() {
        ProviderPlayerGameStat corrected = service.correct(
                "GAME-1",
                7L,
                new ManualPlayerGameCorrectionRequest(null, 10, null, null, null, 45, null),
                "global-admin");

        assertThat(corrected)
                .extracting(
                        ProviderPlayerGameStat::isOverridden,
                        ProviderPlayerGameStat::getOverrideActor,
                        ProviderPlayerGameStat::getOverriddenAt,
                        ProviderPlayerGameStat::getCorrectedParticipated,
                        ProviderPlayerGameStat::getCorrectedKills,
                        ProviderPlayerGameStat::getCorrectedDeaths,
                        ProviderPlayerGameStat::getCorrectedAssists,
                        ProviderPlayerGameStat::getCorrectedCs,
                        ProviderPlayerGameStat::getCorrectedVisionScore,
                        ProviderPlayerGameStat::getCorrectedWin)
                .containsExactly(true, "global-admin", NOW, true, 10, 2, 6, 250, 45, true);
        assertThat(corrected)
                .extracting(
                        ProviderPlayerGameStat::getRawKills,
                        ProviderPlayerGameStat::getRawVisionScore,
                        ProviderPlayerGameStat::isRawWin)
                .containsExactly(4, 20, true);
        assertThat(corrected.getFantasyScore()).isEqualTo(43.5);
        verify(repository).save(stat);
    }

    @Test
    void providerRefreshCanUpdateTheSourceSnapshotWithoutReplacingTheOverride() {
        service.correct(
                "GAME-1",
                7L,
                new ManualPlayerGameCorrectionRequest(true, 10, 1, 8, 300, 45, true),
                "global-admin");
        double overriddenScore = stat.getFantasyScore();

        stat.setRawKills(12);
        stat.setRawDeaths(0);
        stat.setRawAssists(12);
        stat.setRawCs(320);
        stat.setRawVisionScore(50);
        stat.setRawWin(false);

        assertThat(stat.isOverridden()).isTrue();
        assertThat(stat.getCorrectedKills()).isEqualTo(10);
        assertThat(stat.getFantasyScore()).isEqualTo(overriddenScore);
    }

    @Test
    void restoreClearsTheOverrideAndRecalculatesTheLatestProviderSnapshot() {
        service.correct(
                "GAME-1",
                7L,
                new ManualPlayerGameCorrectionRequest(false, 10, 1, 8, 300, 45, true),
                "global-admin");
        stat.setRawKills(12);
        stat.setRawDeaths(0);
        stat.setRawAssists(12);
        stat.setRawCs(320);
        stat.setRawVisionScore(50);
        stat.setRawWin(false);

        ProviderPlayerGameStat restored = service.restore("GAME-1", 7L);

        assertThat(restored.isOverridden()).isFalse();
        assertThat(restored.getOverrideActor()).isNull();
        assertThat(restored.getOverriddenAt()).isNull();
        assertThat(restored.getCorrectedParticipated()).isNull();
        assertThat(restored.getCorrectedKills()).isNull();
        assertThat(restored.getCorrectedDeaths()).isNull();
        assertThat(restored.getCorrectedAssists()).isNull();
        assertThat(restored.getCorrectedCs()).isNull();
        assertThat(restored.getCorrectedVisionScore()).isNull();
        assertThat(restored.getCorrectedWin()).isNull();
        assertThat(restored.getFantasyScore()).isEqualTo(63.2);
    }

    @Test
    void rejectsAnUnknownProviderPlayerGame() {
        when(repository.findByProviderGameExternalGameIdAndLecPlayerId("missing", 7L))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.restore("missing", 7L))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("missing");
    }

    @Test
    void rejectsNegativeCorrectedStatistics() {
        var request = new ManualPlayerGameCorrectionRequest(true, -1, -2, -3, -4, -5, true);

        try (var validatorFactory = Validation.buildDefaultValidatorFactory()) {
            assertThat(validatorFactory.getValidator().validate(request)).hasSize(5);
        }
    }
}
