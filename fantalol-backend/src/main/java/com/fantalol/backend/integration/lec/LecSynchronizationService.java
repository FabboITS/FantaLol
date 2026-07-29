package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.oracle.OracleGameImportService;
import com.fantalol.backend.integration.oracle.OracleImportSummary;
import com.fantalol.backend.integration.oracle.ProviderGame;
import com.fantalol.backend.integration.pandascore.PandaScoreClient;
import com.fantalol.backend.lineup.LineupBackfillService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.Collectors;

@Service
public class LecSynchronizationService {
    public static final String PANDASCORE = "PANDASCORE";
    public static final String ORACLES_ELIXIR = ProviderGame.ORACLES_ELIXIR;
    private static final ReentrantLock ORACLE_SYNCHRONIZATION_LOCK = new ReentrantLock(true);

    private final PandaScoreClient pandaScoreClient;
    private final OracleElixirClient oracleElixirClient;
    private final OracleGameImportService oracleImportService;
    private final LineupBackfillService lineupBackfillService;
    private final ProviderSyncStateService stateService;
    private final LecSyncProperties properties;
    private final Clock clock;

    @Autowired
    public LecSynchronizationService(
            PandaScoreClient pandaScoreClient,
            OracleElixirClient oracleElixirClient,
            OracleGameImportService oracleImportService,
            LineupBackfillService lineupBackfillService,
            ProviderSyncStateService stateService,
            LecSyncProperties properties,
            Clock clock
    ) {
        this.pandaScoreClient = pandaScoreClient;
        this.oracleElixirClient = oracleElixirClient;
        this.oracleImportService = oracleImportService;
        this.lineupBackfillService = lineupBackfillService;
        this.stateService = stateService;
        this.properties = properties;
        this.clock = clock;
    }

    LecSynchronizationService(
            PandaScoreClient pandaScoreClient,
            OracleElixirClient oracleElixirClient,
            OracleGameImportService oracleImportService,
            LineupBackfillService lineupBackfillService,
            ProviderSyncStateRepository stateRepository,
            LecSyncProperties properties,
            ObjectMapper objectMapper,
            Clock clock
    ) {
        this(
                pandaScoreClient,
                oracleElixirClient,
                oracleImportService,
                lineupBackfillService,
                new ProviderSyncStateService(stateRepository, objectMapper, clock),
                properties,
                clock);
    }

    public SyncReport synchronize(SyncTrigger trigger) {
        synchronizePandaScore();
        synchronizeOracle();
        return new SyncReport(clock.instant(), providerStatuses(stateService.all()));
    }

    @Scheduled(cron = "${fantalol.lec.sync-cron:0 15 */6 * * *}")
    public SyncReport scheduledSynchronize() {
        return synchronize(SyncTrigger.SCHEDULED);
    }

    public LecSyncStatusResponse status() {
        List<ProviderSyncState> states = stateService.all();
        Map<String, ProviderSyncState> byProvider = states.stream()
                .collect(Collectors.toMap(ProviderSyncState::getProvider, Function.identity()));
        ProviderSyncState oracle = byProvider.get(ORACLES_ELIXIR);
        Instant lastUpdated = states.stream()
                .map(ProviderSyncState::getLastSuccessAt)
                .filter(java.util.Objects::nonNull)
                .max(Comparator.naturalOrder())
                .orElse(null);
        boolean failed = states.stream().anyMatch(state -> "FAILED".equals(state.getStatus()));
        boolean provisional = !successful(byProvider.get(PANDASCORE)) || !successful(byProvider.get(ORACLES_ELIXIR));
        String status = failed ? "stale" : provisional ? "awaiting-data" : "fresh";
        LecSyncStatusResponse.ImportCounts counts = oracle == null
                ? new LecSyncStatusResponse.ImportCounts(0, 0, 0, 0)
                : new LecSyncStatusResponse.ImportCounts(
                        oracle.getInsertedGames(),
                        oracle.getUpdatedGames(),
                        oracle.getSkippedGames(),
                        oracle.getFailedGames());
        return new LecSyncStatusResponse(
                status,
                lastUpdated,
                provisional,
                providerStatuses(states),
                counts,
                stateService.unmatchedPlayers(oracle));
    }

    private void synchronizePandaScore() {
        try {
            JsonNode matches = pandaScoreClient.getTournamentMatches(properties.tournamentId());
            if (matches == null) {
                throw new IllegalStateException("PandaScore returned no tournament matches");
            }
            stateService.recordPandaSuccess(matches.toString());
        } catch (RuntimeException exception) {
            stateService.recordPandaFailure(exception);
        }
    }

    private void synchronizeOracle() {
        ORACLE_SYNCHRONIZATION_LOCK.lock();
        try {
            String csv = oracleElixirClient.download();
            lineupBackfillService.backfill();
            OracleImportSummary summary =
                    oracleImportService.importCsvOrThrow(csv, properties.league(), properties.split());
            if (summary.isSuccessfulImport()) {
                stateService.recordOracleSuccess(summary);
            } else {
                stateService.recordOracleFailure(summary);
            }
        } catch (RuntimeException exception) {
            stateService.recordOracleFailure(exception);
        } finally {
            ORACLE_SYNCHRONIZATION_LOCK.unlock();
        }
    }

    private List<SyncReport.ProviderStatus> providerStatuses(List<ProviderSyncState> states) {
        Map<String, ProviderSyncState> byProvider = states.stream()
                .collect(Collectors.toMap(ProviderSyncState::getProvider, Function.identity()));
        return List.of(PANDASCORE, ORACLES_ELIXIR).stream()
                .map(provider -> byProvider.containsKey(provider)
                        ? status(byProvider.get(provider))
                        : new SyncReport.ProviderStatus(provider, "AWAITING_DATA", null, null, null))
                .toList();
    }

    private static SyncReport.ProviderStatus status(ProviderSyncState state) {
        return new SyncReport.ProviderStatus(
                state.getProvider(),
                state.getStatus(),
                state.getLastAttemptAt(),
                state.getLastSuccessAt(),
                state.getLastError());
    }

    private static boolean successful(ProviderSyncState state) {
        return state != null && state.getLastSuccessAt() != null;
    }
}
