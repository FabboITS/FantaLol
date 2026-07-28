package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.oracle.OracleImportSummary;
import com.fantalol.backend.integration.oracle.ProviderGame;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ProviderSyncStateService {
    private static final String SUCCESS = "SUCCESS";
    private static final String FAILED = "FAILED";

    private final ProviderSyncStateRepository repository;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordPandaSuccess(String providerSnapshot) {
        Instant now = clock.instant();
        ProviderSyncState state = state(LecSynchronizationService.PANDASCORE);
        state.setStatus(SUCCESS);
        state.setLastAttemptAt(now);
        state.setLastSuccessAt(now);
        state.setLastError(null);
        state.setProviderSnapshot(providerSnapshot);
        repository.save(state);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordPandaFailure(RuntimeException exception) {
        recordFailure(LecSynchronizationService.PANDASCORE, exception);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordOracleSuccess(OracleImportSummary summary) {
        Instant now = clock.instant();
        ProviderSyncState state = state(ProviderGame.ORACLES_ELIXIR);
        state.setStatus(SUCCESS);
        state.setLastAttemptAt(now);
        state.setLastSuccessAt(now);
        state.setLastError(null);
        state.setInsertedGames(summary.insertedGames());
        state.setUpdatedGames(summary.updatedGames());
        state.setSkippedGames(summary.skippedGames());
        state.setFailedGames(summary.failedGames());
        state.setUnmatchedPlayers(writeUnmatchedPlayers(summary.unmatchedPlayers()));
        repository.save(state);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordOracleFailure(RuntimeException exception) {
        ProviderSyncState state = recordFailure(ProviderGame.ORACLES_ELIXIR, exception);
        state.setInsertedGames(0);
        state.setUpdatedGames(0);
        state.setSkippedGames(0);
        state.setFailedGames(1);
        state.setUnmatchedPlayers("[]");
        repository.save(state);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordOracleFailure(OracleImportSummary summary) {
        ProviderSyncState state = state(ProviderGame.ORACLES_ELIXIR);
        state.setStatus(FAILED);
        state.setLastAttemptAt(clock.instant());
        state.setLastError(summary.failureMessage());
        state.setInsertedGames(summary.insertedGames());
        state.setUpdatedGames(summary.updatedGames());
        state.setSkippedGames(summary.skippedGames());
        state.setFailedGames(summary.diagnosticFailedGames());
        state.setUnmatchedPlayers(writeUnmatchedPlayers(summary.unmatchedPlayers()));
        repository.save(state);
    }

    @Transactional(readOnly = true)
    public List<ProviderSyncState> all() {
        return repository.findAll();
    }

    public List<String> unmatchedPlayers(ProviderSyncState state) {
        if (state == null || state.getUnmatchedPlayers() == null || state.getUnmatchedPlayers().isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(state.getUnmatchedPlayers(), new TypeReference<>() {
            });
        } catch (JsonProcessingException exception) {
            return List.of();
        }
    }

    private ProviderSyncState recordFailure(String provider, RuntimeException exception) {
        ProviderSyncState state = state(provider);
        state.setStatus(FAILED);
        state.setLastAttemptAt(clock.instant());
        state.setLastError(message(exception));
        repository.save(state);
        return state;
    }

    private ProviderSyncState state(String provider) {
        return repository.findByProvider(provider)
                .orElseGet(() -> ProviderSyncState.builder().provider(provider).build());
    }

    private String writeUnmatchedPlayers(List<String> unmatchedPlayers) {
        try {
            return objectMapper.writeValueAsString(unmatchedPlayers);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Unable to store unmatched Oracle players", exception);
        }
    }

    private static String message(RuntimeException exception) {
        String message = exception.getMessage() == null
                ? exception.getClass().getSimpleName()
                : exception.getMessage();
        return message.substring(0, Math.min(message.length(), 1000));
    }
}
