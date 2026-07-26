package com.fantalol.backend.integration.oracle;

import java.time.Instant;

public record OracleSyncHealth(
        String status,
        Instant lastAttemptAt,
        Instant lastSuccessAt,
        String etag,
        int processedMatchdays,
        String message
) {
}
