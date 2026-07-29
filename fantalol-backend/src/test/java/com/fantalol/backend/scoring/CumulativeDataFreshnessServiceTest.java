package com.fantalol.backend.scoring;

import com.fantalol.backend.integration.lec.ProviderSyncState;
import com.fantalol.backend.integration.lec.ProviderSyncStateRepository;
import com.fantalol.backend.integration.oracle.ProviderGame;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class CumulativeDataFreshnessServiceTest {

    private final ProviderSyncStateRepository repository = mock(ProviderSyncStateRepository.class);
    private final CumulativeDataFreshnessService service = new CumulativeDataFreshnessService(repository);

    @Test
    void successfulOracleImportPublishesFreshItemsWithLastSuccessTime() {
        Instant lastSuccess = Instant.parse("2026-07-28T14:00:00Z");
        when(repository.findByProvider(ProviderGame.ORACLES_ELIXIR)).thenReturn(Optional.of(
                ProviderSyncState.builder().provider(ProviderGame.ORACLES_ELIXIR)
                        .status("SUCCESS").lastSuccessAt(lastSuccess).build()));

        var response = service.wrap(List.of("score"));

        assertThat(response.status()).isEqualTo("fresh");
        assertThat(response.lastUpdatedAt()).isEqualTo(lastSuccess);
        assertThat(response.provisional()).isFalse();
        assertThat(response.items()).containsExactly("score");
    }

    @Test
    void failedOracleRefreshKeepsLastSuccessfulItemsButMarksThemStale() {
        Instant lastSuccess = Instant.parse("2026-07-28T12:00:00Z");
        when(repository.findByProvider(ProviderGame.ORACLES_ELIXIR)).thenReturn(Optional.of(
                ProviderSyncState.builder().provider(ProviderGame.ORACLES_ELIXIR)
                        .status("FAILED").lastSuccessAt(lastSuccess)
                        .lastError("private provider failure").unmatchedPlayers("[\"Hidden\"]")
                        .providerSnapshot("private snapshot").failedGames(7).build()));

        var response = service.wrap(List.of("last-known-good"));

        assertThat(response.status()).isEqualTo("stale");
        assertThat(response.lastUpdatedAt()).isEqualTo(lastSuccess);
        assertThat(response.provisional()).isTrue();
        assertThat(response.items()).containsExactly("last-known-good");
        assertThat(Arrays.stream(response.getClass().getRecordComponents())
                .map(component -> component.getName()))
                .containsExactly("status", "lastUpdatedAt", "provisional", "items");
    }

    @Test
    void missingFirstOracleSuccessPublishesAwaitingState() {
        when(repository.findByProvider(ProviderGame.ORACLES_ELIXIR)).thenReturn(Optional.empty());

        var response = service.wrap(List.of());

        assertThat(response.status()).isEqualTo("awaiting-data");
        assertThat(response.lastUpdatedAt()).isNull();
        assertThat(response.provisional()).isTrue();
        assertThat(response.items()).isEmpty();
    }
}
