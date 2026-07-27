package com.fantalol.backend.integration.lec;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "fantalol.lec")
public record LecSyncProperties(long tournamentId, String league, String split, String oracleCsvUrl) {
}
