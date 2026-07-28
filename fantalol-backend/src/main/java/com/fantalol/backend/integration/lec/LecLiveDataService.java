package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStatRepository;
import com.fantalol.backend.integration.pandascore.PandaScoreClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

@Service
public class LecLiveDataService {
    private final ProviderSyncStateRepository syncStateRepository;
    private final ProviderPlayerGameStatRepository statRepository;
    private final ObjectMapper objectMapper;
    private final PandaScoreClient legacyPandaScoreClient;
    private final OracleElixirClient legacyOracleElixirClient;
    private final LecSyncProperties legacyProperties;
    private final LecDataParser parser;
    private final AtomicReference<LecDataSnapshot> snapshot = new AtomicReference<>(LecDataSnapshot.empty());

    @Autowired
    public LecLiveDataService(
            ProviderSyncStateRepository syncStateRepository,
            ProviderPlayerGameStatRepository statRepository,
            LecDataParser parser,
            ObjectMapper objectMapper
    ) {
        this.syncStateRepository = syncStateRepository;
        this.statRepository = statRepository;
        this.parser = parser;
        this.objectMapper = objectMapper;
        this.legacyPandaScoreClient = null;
        this.legacyOracleElixirClient = null;
        this.legacyProperties = null;
    }

    LecLiveDataService(
            PandaScoreClient pandaScoreClient,
            OracleElixirClient oracleElixirClient,
            LecDataParser parser,
            LecSyncProperties properties
    ) {
        this.syncStateRepository = null;
        this.statRepository = null;
        this.objectMapper = null;
        this.legacyPandaScoreClient = pandaScoreClient;
        this.legacyOracleElixirClient = oracleElixirClient;
        this.parser = parser;
        this.legacyProperties = properties;
    }

    /**
     * Compatibility entry point retained for callers of the original live-data service.
     * Production scheduling and administrator synchronization use {@link LecSynchronizationService}.
     */
    public LecDataSnapshot synchronize() {
        try {
            LecDataSnapshot fresh = parser.parse(
                    legacyPandaScoreClient.getTournamentMatches(legacyProperties.tournamentId()),
                    legacyOracleElixirClient.download(),
                    legacyProperties.league(),
                    legacyProperties.split()
            );
            snapshot.set(fresh);
            return fresh;
        } catch (RuntimeException exception) {
            LecDataSnapshot previous = snapshot.get();
            LecDataSnapshot stale = new LecDataSnapshot(
                    previous.lastUpdatedAt() == null ? "awaiting-data" : "stale",
                    previous.lastUpdatedAt(),
                    previous.provisional(),
                    previous.standings(),
                    previous.performances(),
                    previous.matches()
            );
            snapshot.set(stale);
            return stale;
        }
    }

    @Transactional(readOnly = true)
    public LecDataSnapshot current() {
        if (syncStateRepository == null) {
            return snapshot.get();
        }
        List<ProviderSyncState> states = syncStateRepository.findAll();
        Optional<ProviderSyncState> panda = states.stream()
                .filter(state -> LecSynchronizationService.PANDASCORE.equals(state.getProvider()))
                .findFirst();
        JsonNode pandaMatches = panda.map(ProviderSyncState::getProviderSnapshot)
                .filter(value -> !value.isBlank())
                .map(this::readTree)
                .orElse(null);
        Instant lastUpdatedAt = states.stream()
                .map(ProviderSyncState::getLastSuccessAt)
                .filter(java.util.Objects::nonNull)
                .max(Comparator.naturalOrder())
                .orElse(null);
        boolean failed = states.stream().anyMatch(state -> "FAILED".equals(state.getStatus()));
        boolean hasPandaData = panda.map(ProviderSyncState::getLastSuccessAt).isPresent();
        boolean hasOracleData = states.stream()
                .filter(state -> LecSynchronizationService.ORACLES_ELIXIR.equals(state.getProvider()))
                .map(ProviderSyncState::getLastSuccessAt)
                .anyMatch(java.util.Objects::nonNull);
        String status = failed ? "stale" : hasPandaData && hasOracleData ? "fresh" : "awaiting-data";
        return parser.project(
                pandaMatches,
                statRepository.findAllByOrderByProviderGamePlayedAtAsc(),
                status,
                lastUpdatedAt);
    }

    private JsonNode readTree(String value) {
        try {
            return objectMapper.readTree(value);
        } catch (Exception exception) {
            return null;
        }
    }
}
