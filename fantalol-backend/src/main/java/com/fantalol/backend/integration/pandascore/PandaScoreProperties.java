package com.fantalol.backend.integration.pandascore;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "fantalol.pandascore")
public record PandaScoreProperties(String baseUrl, String token, String summerTournamentIds) {
}
