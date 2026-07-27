package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.pandascore.PandaScoreClient;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class LecLiveDataServiceTest {
    @Test
    void keepsTheLastCompleteSnapshotWhenAProviderFails() throws Exception {
        PandaScoreClient pandaScore = mock(PandaScoreClient.class);
        OracleElixirClient oracle = mock(OracleElixirClient.class);
        LecDataParser parser = mock(LecDataParser.class);
        LecSyncProperties properties = new LecSyncProperties(42, "LEC", "Summer", "https://example.test/data.csv");
        LecDataSnapshot complete = new LecDataSnapshot(
                "fresh", java.time.Instant.now(), false, java.util.List.of(), java.util.List.of(), java.util.List.of());
        when(pandaScore.getTournamentMatches(42)).thenReturn(new ObjectMapper().readTree("[]"));
        when(oracle.download()).thenReturn("csv");
        when(parser.parse(any(), eq("csv"), eq("LEC"), eq("Summer"))).thenReturn(complete);
        LecLiveDataService service = new LecLiveDataService(pandaScore, oracle, parser, properties);

        assertThat(service.synchronize().status()).isEqualTo("fresh");
        when(oracle.download()).thenThrow(new IllegalStateException("offline"));

        assertThat(service.synchronize().status()).isEqualTo("stale");
        assertThat(service.current().lastUpdatedAt()).isEqualTo(complete.lastUpdatedAt());
    }
}
