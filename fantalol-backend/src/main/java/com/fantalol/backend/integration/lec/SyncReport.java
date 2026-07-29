package com.fantalol.backend.integration.lec;

import java.time.Instant;
import java.util.List;

public record SyncReport(
        Instant completedAt,
        List<ProviderStatus> providers
) {
    public record ProviderStatus(
            String provider,
            String status,
            Instant lastAttemptAt,
            Instant lastSuccessAt,
            String lastError
    ) {
    }
}
