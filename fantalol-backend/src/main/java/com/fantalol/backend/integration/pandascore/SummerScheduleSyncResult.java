package com.fantalol.backend.integration.pandascore;

import java.time.Instant;

public record SummerScheduleSyncResult(
        Instant synchronizedAt,
        int officialSeries,
        int createdMatchdays,
        int linkedMatchdays
) {
}
