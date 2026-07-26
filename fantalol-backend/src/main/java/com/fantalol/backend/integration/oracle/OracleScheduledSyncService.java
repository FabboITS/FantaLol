package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.matchday.MatchdayRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.time.Instant;
import java.util.concurrent.atomic.AtomicReference;

@Service
@RequiredArgsConstructor
public class OracleScheduledSyncService {
    private final MatchdayRepository matchdayRepository;
    private final OracleGameCsvIngestionService importer;
    private final AtomicReference<OracleSyncHealth> health = new AtomicReference<>(
            new OracleSyncHealth("NOT_RUN", null, null, null, 0, "No synchronization attempted"));

    @Value("${fantalol.oracle.csv-url:}")
    private String csvUrl;

    @Value("${fantalol.oracle.league:LEC}")
    private String league;

    @Value("${fantalol.oracle.split:Summer}")
    private String split;

    private String etag;

    @Scheduled(cron = "${fantalol.oracle.sync-cron:0 15 4 * * *}", zone = "Europe/Rome")
    public void scheduledSync() {
        if (csvUrl != null && !csvUrl.isBlank()) sync();
    }

    public synchronized OracleSyncHealth sync() {
        Instant attempt = Instant.now();
        try {
            RestClient.RequestHeadersSpec<?> request = RestClient.create().get()
                    .uri(csvUrl)
                    .accept(MediaType.parseMediaType("text/csv"), MediaType.APPLICATION_OCTET_STREAM);
            if (etag != null) request = request.header(HttpHeaders.IF_NONE_MATCH, etag);
            ResponseEntity<byte[]> response = request.retrieve().toEntity(byte[].class);
            if (response.getStatusCode() == HttpStatus.NOT_MODIFIED) {
                OracleSyncHealth current = health.get();
                return update(new OracleSyncHealth("UNCHANGED", attempt, current.lastSuccessAt(), etag, 0,
                        "Remote dataset has not changed"));
            }
            byte[] body = response.getBody();
            if (body == null || body.length == 0 || !looksLikeCsv(body)) {
                throw new IllegalStateException("Oracle response is empty or is not a CSV dataset");
            }
            String responseEtag = response.getHeaders().getETag();
            int processed = 0;
            InMemoryMultipartFile file = new InMemoryMultipartFile("oracle-2026.csv", body);
            for (var matchday : matchdayRepository.findAll()) {
                if (matchday.getData() != null) {
                    importer.importCsv(matchday.getId(), file, league, split);
                    processed++;
                }
            }
            etag = responseEtag;
            return update(new OracleSyncHealth("HEALTHY", attempt, Instant.now(), etag, processed,
                    "Oracle dataset synchronized"));
        } catch (Exception exception) {
            OracleSyncHealth current = health.get();
            return update(new OracleSyncHealth("DEGRADED", attempt, current.lastSuccessAt(), etag, 0,
                    exception.getMessage()));
        }
    }

    public OracleSyncHealth health() {
        return health.get();
    }

    private OracleSyncHealth update(OracleSyncHealth value) {
        health.set(value);
        return value;
    }

    private static boolean looksLikeCsv(byte[] bytes) {
        String prefix = new String(bytes, 0, Math.min(bytes.length, 300), java.nio.charset.StandardCharsets.UTF_8);
        return prefix.contains("gameid") && prefix.contains("playername") && prefix.contains(",");
    }
}
