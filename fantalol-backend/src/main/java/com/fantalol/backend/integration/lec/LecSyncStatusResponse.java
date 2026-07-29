package com.fantalol.backend.integration.lec;

import java.time.Instant;
import java.util.List;

public record LecSyncStatusResponse(
        String status,
        Instant lastUpdatedAt,
        boolean provisional,
        List<SyncReport.ProviderStatus> providers,
        ImportCounts counts,
        List<String> unmatchedPlayers
) {
    public LecSyncStatusResponse {
        providers = List.copyOf(providers);
        unmatchedPlayers = List.copyOf(unmatchedPlayers);
    }

    public record ImportCounts(
            int insertedGames,
            int updatedGames,
            int skippedGames,
            int failedGames
    ) {
    }
}
