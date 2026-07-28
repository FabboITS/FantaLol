package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.integration.lec.ProviderSyncState;
import com.fantalol.backend.integration.lec.ProviderSyncStateRepository;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.LecPlayerRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.concurrent.locks.ReentrantLock;

@Service
public class OracleGameImportService {
    private static final String ORACLE_PROVIDER = ProviderGame.ORACLES_ELIXIR;
    private static final String SUCCESS = "SUCCESS";
    private static final String FAILED = "FAILED";
    private static final ReentrantLock IMPORT_LOCK = new ReentrantLock(true);

    private final OracleElixirGameParser parser;
    private final OracleGameImportPersistenceService persistenceService;
    private final ProviderSyncStateRepository providerSyncStateRepository;

    @Autowired
    public OracleGameImportService(
            OracleElixirGameParser parser,
            OracleGameImportPersistenceService persistenceService,
            ProviderSyncStateRepository providerSyncStateRepository
    ) {
        this.parser = parser;
        this.persistenceService = persistenceService;
        this.providerSyncStateRepository = providerSyncStateRepository;
    }

    OracleGameImportService(
            OracleElixirGameParser parser,
            ProviderGameRepository providerGameRepository,
            ProviderPlayerGameStatRepository playerGameStatRepository,
            LecPlayerRepository lecPlayerRepository,
            GameScoreCalculator gameScoreCalculator,
            ProviderSyncStateRepository providerSyncStateRepository
    ) {
        this(
                parser,
                new OracleGameImportPersistenceService(
                        providerGameRepository,
                        playerGameStatRepository,
                        lecPlayerRepository,
                        gameScoreCalculator),
                providerSyncStateRepository);
    }

    public OracleImportSummary importCsv(String csv, String league, String split) {
        try {
            OracleImportSummary summary = importCsvOrThrow(csv, league, split);
            if (summary.isSuccessfulImport()) {
                recordOracleSuccess(summary);
            } else {
                recordOracleFailure(summary);
            }
            return summary;
        } catch (RuntimeException exception) {
            recordOracleFailure(exception);
            return new OracleImportSummary(0, 0, 0, 1, List.of());
        }
    }

    public OracleImportSummary importCsvOrThrow(String csv, String league, String split) {
        IMPORT_LOCK.lock();
        try {
            List<OracleGameBatch> batches = parser.parse(csv, league, split);
            return persistenceService.importBatches(batches, league, split);
        } finally {
            IMPORT_LOCK.unlock();
        }
    }

    public void recordOracleSuccess(OracleImportSummary summary) {
        Instant now = Instant.now();
        ProviderSyncState state = providerSyncStateRepository.findByProvider(ORACLE_PROVIDER)
                .orElseGet(() -> ProviderSyncState.builder().provider(ORACLE_PROVIDER).build());
        state.setStatus(SUCCESS);
        state.setLastAttemptAt(now);
        state.setLastSuccessAt(now);
        state.setLastError(null);
        state.setInsertedGames(summary.insertedGames());
        state.setUpdatedGames(summary.updatedGames());
        state.setSkippedGames(summary.skippedGames());
        state.setFailedGames(summary.failedGames());
        state.setUnmatchedPlayers(jsonArray(summary.unmatchedPlayers()));
        providerSyncStateRepository.save(state);
    }

    public void recordOracleFailure(RuntimeException exception) {
        ProviderSyncState state = providerSyncStateRepository.findByProvider(ORACLE_PROVIDER)
                .orElseGet(() -> ProviderSyncState.builder().provider(ORACLE_PROVIDER).build());
        state.setStatus(FAILED);
        state.setLastAttemptAt(Instant.now());
        String message = exception.getMessage() == null ? exception.getClass().getSimpleName() : exception.getMessage();
        state.setLastError(message.substring(0, Math.min(message.length(), 1000)));
        state.setInsertedGames(0);
        state.setUpdatedGames(0);
        state.setSkippedGames(0);
        state.setFailedGames(1);
        state.setUnmatchedPlayers("[]");
        providerSyncStateRepository.save(state);
    }

    public void recordOracleFailure(OracleImportSummary summary) {
        ProviderSyncState state = providerSyncStateRepository.findByProvider(ORACLE_PROVIDER)
                .orElseGet(() -> ProviderSyncState.builder().provider(ORACLE_PROVIDER).build());
        state.setStatus(FAILED);
        state.setLastAttemptAt(Instant.now());
        state.setLastError(summary.failureMessage());
        state.setInsertedGames(summary.insertedGames());
        state.setUpdatedGames(summary.updatedGames());
        state.setSkippedGames(summary.skippedGames());
        state.setFailedGames(summary.diagnosticFailedGames());
        state.setUnmatchedPlayers(jsonArray(summary.unmatchedPlayers()));
        providerSyncStateRepository.save(state);
    }

    private static String jsonArray(List<String> values) {
        return values.stream()
                .map(value -> "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"")
                .collect(java.util.stream.Collectors.joining(",", "[", "]"));
    }
}
