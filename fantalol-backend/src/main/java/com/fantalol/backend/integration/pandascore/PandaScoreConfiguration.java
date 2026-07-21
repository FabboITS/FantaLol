package com.fantalol.backend.integration.pandascore;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties(PandaScoreProperties.class)
public class PandaScoreConfiguration {
    @Bean
    RestClient pandaScoreRestClient(PandaScoreProperties properties) {
        RestClient.Builder builder = RestClient.builder().baseUrl(properties.baseUrl());
        if (properties.token() != null && !properties.token().isBlank()) {
            builder.defaultHeader("Authorization", "Bearer " + properties.token());
        }
        return builder.defaultHeader("Accept", "application/json").build();
    }
}
