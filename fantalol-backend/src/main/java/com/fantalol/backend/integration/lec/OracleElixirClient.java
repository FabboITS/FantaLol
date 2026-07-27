package com.fantalol.backend.integration.lec;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@RequiredArgsConstructor
public class OracleElixirClient {
    private final LecSyncProperties properties;

    public String download() {
        if (properties.oracleCsvUrl() == null || properties.oracleCsvUrl().isBlank()) {
            throw new IllegalStateException("ORACLE_ELIXIR_CSV_URL is not configured");
        }
        return RestClient.create()
                .get()
                .uri(properties.oracleCsvUrl())
                .retrieve()
                .body(String.class);
    }
}
