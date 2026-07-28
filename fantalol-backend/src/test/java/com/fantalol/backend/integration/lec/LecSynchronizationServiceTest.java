package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.oracle.OracleGameImportService;
import com.fantalol.backend.integration.oracle.OracleImportSummary;
import com.fantalol.backend.integration.oracle.PlayerGameCorrectionService;
import com.fantalol.backend.integration.pandascore.PandaScoreClient;
import com.fantalol.backend.lineup.LineupBackfillService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Collections;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class LecSynchronizationServiceTest {
    private static final Instant NOW = Instant.parse("2026-07-28T12:00:00Z");

    private final PandaScoreClient pandaScoreClient = mock(PandaScoreClient.class);
    private final OracleElixirClient oracleElixirClient = mock(OracleElixirClient.class);
    private final OracleGameImportService oracleImportService = mock(OracleGameImportService.class);
    private final LineupBackfillService lineupBackfillService = mock(LineupBackfillService.class);
    private final ProviderSyncStateRepository syncStateRepository = mock(ProviderSyncStateRepository.class);
    private final Map<String, ProviderSyncState> states =
            Collections.synchronizedMap(new LinkedHashMap<>());
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final LecSyncProperties properties =
            new LecSyncProperties(42L, "LEC", "Summer", ZoneId.of("Europe/Rome"),
                    OffsetDateTime.parse("2026-07-24T00:00:00+02:00"),
                    "https://example.test/oracle.csv");
    private LecSynchronizationService service;

    @BeforeEach
    void setUp() {
        when(syncStateRepository.findByProvider(any()))
                .thenAnswer(invocation -> Optional.ofNullable(states.get(invocation.getArgument(0))));
        when(syncStateRepository.findAll()).thenAnswer(invocation -> {
            synchronized (states) {
                return List.copyOf(states.values());
            }
        });
        when(syncStateRepository.save(any(ProviderSyncState.class))).thenAnswer(invocation -> {
            ProviderSyncState state = invocation.getArgument(0);
            states.put(state.getProvider(), state);
            return state;
        });
        when(oracleImportService.importCsvOrThrow(any(), any(), any()))
                .thenReturn(new OracleImportSummary(1, 0, 0, 0, List.of()));

        service = new LecSynchronizationService(
                pandaScoreClient,
                oracleElixirClient,
                oracleImportService,
                lineupBackfillService,
                syncStateRepository,
                properties,
                objectMapper,
                Clock.fixed(NOW, ZoneOffset.UTC));
    }

    @Test
    void oracleFailureDoesNotDiscardPersistedPandaStandings() throws Exception {
        JsonNode standings = objectMapper.readTree("""
                [{"status":"finished","winner_id":1,
                  "opponents":[
                    {"opponent":{"id":1,"name":"G2 Esports"}},
                    {"opponent":{"id":2,"name":"Fnatic"}}]}]
                """);
        when(pandaScoreClient.getTournamentMatches(42L)).thenReturn(standings);
        when(oracleElixirClient.download()).thenThrow(new IllegalStateException("Oracle unavailable"));

        service.synchronize(SyncTrigger.MANUAL);

        ProviderSyncState panda = states.get(LecSynchronizationService.PANDASCORE);
        assertThat(panda.getStatus()).isEqualTo("SUCCESS");
        assertThat(panda.getProviderSnapshot()).isEqualTo(standings.toString());
        assertThat(states.get(LecSynchronizationService.ORACLES_ELIXIR).getLastError())
                .isEqualTo("Oracle unavailable");
    }

    @Test
    void pandaFailureDoesNotStopOracleImportOrReplaceItsLastValidProjection() {
        ProviderSyncState panda = ProviderSyncState.builder()
                .provider(LecSynchronizationService.PANDASCORE)
                .status("SUCCESS")
                .lastAttemptAt(NOW.minusSeconds(7200))
                .lastSuccessAt(NOW.minusSeconds(7200))
                .providerSnapshot("[{\"status\":\"finished\"}]")
                .build();
        states.put(panda.getProvider(), panda);
        when(pandaScoreClient.getTournamentMatches(42L))
                .thenThrow(new IllegalStateException("Panda unavailable"));
        when(oracleElixirClient.download()).thenReturn("oracle-csv");

        service.synchronize(SyncTrigger.MANUAL);

        assertThat(states.get(LecSynchronizationService.PANDASCORE))
                .extracting(ProviderSyncState::getStatus, ProviderSyncState::getProviderSnapshot)
                .containsExactly("FAILED", "[{\"status\":\"finished\"}]");
        verify(oracleImportService).importCsvOrThrow("oracle-csv", "LEC", "Summer");
    }

    @Test
    void backfillsBeforeEveryOracleAttributionAndIsSafeToRepeat() throws Exception {
        when(pandaScoreClient.getTournamentMatches(42L)).thenReturn(objectMapper.readTree("[]"));
        when(oracleElixirClient.download()).thenReturn("oracle-csv");

        service.synchronize(SyncTrigger.SCHEDULED);
        service.synchronize(SyncTrigger.MANUAL);

        var order = inOrder(lineupBackfillService, oracleImportService);
        order.verify(lineupBackfillService).backfill();
        order.verify(oracleImportService).importCsvOrThrow("oracle-csv", "LEC", "Summer");
        order.verify(lineupBackfillService).backfill();
        order.verify(oracleImportService).importCsvOrThrow("oracle-csv", "LEC", "Summer");
    }

    @Test
    void scheduledAndManualEntryPointsCallTheSamePublicSynchronizationMethod() {
        LecSynchronizationService observed = spy(service);
        LecDataController controller = new LecDataController(
                mock(LecLiveDataService.class),
                observed,
                mock(PlayerGameCorrectionService.class));

        observed.scheduledSynchronize();
        controller.synchronize();

        verify(observed).synchronize(SyncTrigger.SCHEDULED);
        verify(observed).synchronize(SyncTrigger.MANUAL);
    }

    @Test
    void failedBackfillPreventsOracleAttributionWithoutDowngradingPanda() throws Exception {
        JsonNode standings = objectMapper.readTree("[]");
        when(pandaScoreClient.getTournamentMatches(42L)).thenReturn(standings);
        when(oracleElixirClient.download()).thenReturn("oracle-csv");
        org.mockito.Mockito.doThrow(new IllegalStateException("Backfill failed"))
                .when(lineupBackfillService).backfill();

        service.synchronize(SyncTrigger.MANUAL);

        assertThat(states.get(LecSynchronizationService.PANDASCORE).getStatus()).isEqualTo("SUCCESS");
        assertThat(states.get(LecSynchronizationService.ORACLES_ELIXIR).getLastError())
                .isEqualTo("Backfill failed");
        verify(oracleImportService, never()).importCsvOrThrow(any(), any(), any());
    }

    @Test
    void concurrentTriggersSerializeBackfillAndOracleImport() throws Exception {
        when(pandaScoreClient.getTournamentMatches(42L)).thenReturn(objectMapper.readTree("[]"));
        when(oracleElixirClient.download()).thenReturn("oracle-csv");
        AtomicInteger activeBackfills = new AtomicInteger();
        AtomicInteger maximumConcurrentBackfills = new AtomicInteger();
        org.mockito.Mockito.doAnswer(invocation -> {
            int active = activeBackfills.incrementAndGet();
            maximumConcurrentBackfills.accumulateAndGet(active, Math::max);
            Thread.sleep(75);
            activeBackfills.decrementAndGet();
            return null;
        }).when(lineupBackfillService).backfill();
        when(oracleImportService.importCsvOrThrow("oracle-csv", "LEC", "Summer"))
                .thenReturn(new OracleImportSummary(1, 0, 0, 0, List.of()))
                .thenReturn(new OracleImportSummary(0, 0, 1, 0, List.of()));
        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        try {
            Future<SyncReport> scheduled = executor.submit(() -> synchronizeAfter(ready, start, SyncTrigger.SCHEDULED));
            Future<SyncReport> manual = executor.submit(() -> synchronizeAfter(ready, start, SyncTrigger.MANUAL));
            assertThat(ready.await(1, TimeUnit.SECONDS)).isTrue();
            start.countDown();

            assertThat(List.of(scheduled.get(2, TimeUnit.SECONDS), manual.get(2, TimeUnit.SECONDS)))
                    .allSatisfy(report -> assertThat(report.providers())
                            .filteredOn(provider -> provider.provider().equals(LecSynchronizationService.ORACLES_ELIXIR))
                            .singleElement()
                            .extracting(SyncReport.ProviderStatus::status)
                            .isEqualTo("SUCCESS"));
        } finally {
            executor.shutdownNow();
        }

        assertThat(maximumConcurrentBackfills).hasValue(1);
        assertThat(states.get(LecSynchronizationService.ORACLES_ELIXIR).getFailedGames()).isZero();
        verify(oracleImportService, times(2)).importCsvOrThrow("oracle-csv", "LEC", "Summer");
    }

    private SyncReport synchronizeAfter(CountDownLatch ready, CountDownLatch start, SyncTrigger trigger)
            throws InterruptedException {
        ready.countDown();
        assertThat(start.await(1, TimeUnit.SECONDS)).isTrue();
        return service.synchronize(trigger);
    }
}
