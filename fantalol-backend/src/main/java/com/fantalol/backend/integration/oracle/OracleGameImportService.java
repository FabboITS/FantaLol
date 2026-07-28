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
        IMPORT_LOCK.lock();
        try {
            List<OracleGameBatch> batches = parser.parse(csv, league, split);
            OracleImportSummary summary = persistenceService.importBatches(batches, league, split);
            recordOracleSuccess();
            return summary;
        } catch (RuntimeException exception) {
            recordOracleFailure(exception);
            return new OracleImportSummary(0, 0, 0, 1, List.of());
        } finally {
            IMPORT_LOCK.unlock();
        }
    }

    public void recordOracleSuccess() {
        Instant now = Instant.now();
        ProviderSyncState state = providerSyncStateRepository.findByProvider(ORACLE_PROVIDER)
                .orElseGet(() -> ProviderSyncState.builder().provider(ORACLE_PROVIDER).build());
        state.setStatus(SUCCESS);
        state.setLastAttemptAt(now);
        state.setLastSuccessAt(now);
        state.setLastError(null);
        providerSyncStateRepository.save(state);
    }

    public void recordOracleFailure(RuntimeException exception) {
        ProviderSyncState state = providerSyncStateRepository.findByProvider(ORACLE_PROVIDER)
                .orElseGet(() -> ProviderSyncState.builder().provider(ORACLE_PROVIDER).build());
        state.setStatus(FAILED);
        state.setLastAttemptAt(Instant.now());
        state.setLastError(exception.getMessage() == null ? exception.getClass().getSimpleName() : exception.getMessage());
        providerSyncStateRepository.save(state);
    }

}
