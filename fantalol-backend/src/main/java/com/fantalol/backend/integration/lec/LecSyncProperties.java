package com.fantalol.backend.integration.lec;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.OffsetDateTime;
import java.time.ZoneId;

@ConfigurationProperties(prefix = "fantalol.lec")
public record LecSyncProperties(
        long tournamentId,
        String league,
        String split,
        ZoneId timezone,
        OffsetDateTime backfillFrom,
        String oracleCsvUrl
) {
}
