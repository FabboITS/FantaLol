package com.fantalol.backend.scoring.dto;

import java.time.Instant;
import java.util.List;

public record CumulativeDataResponse<T>(
        String status,
        Instant lastUpdatedAt,
        boolean provisional,
        List<T> items
) {
}
