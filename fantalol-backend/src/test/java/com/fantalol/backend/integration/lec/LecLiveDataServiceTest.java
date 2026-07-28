package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.oracle.ProviderGame;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStatRepository;
import com.fantalol.backend.integration.pandascore.PandaScoreClient;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

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

    @Test
    void rebuildsOracleProjectionFromPersistedGamesWhenPandaFails() {
        ProviderSyncStateRepository stateRepository = mock(ProviderSyncStateRepository.class);
        ProviderPlayerGameStatRepository statRepository = mock(ProviderPlayerGameStatRepository.class);
        when(stateRepository.findAll()).thenReturn(List.of(
                pandaState("FAILED", "Panda unavailable"),
                oracleState("SUCCESS", null)));
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(List.of(stat()));
        LecLiveDataService service = new LecLiveDataService(
                stateRepository,
                statRepository,
                new LecDataParser(new GameScoreCalculator()),
                new ObjectMapper());

        LecDataSnapshot snapshot = service.current();

        assertThat(snapshot.status()).isEqualTo("stale");
        assertThat(snapshot.performances()).singleElement()
                .extracting(LecDataSnapshot.PlayerPerformance::nickname,
                        LecDataSnapshot.PlayerPerformance::gamesPlayed,
                        LecDataSnapshot.PlayerPerformance::fantasyAverage)
                .containsExactly("Caps", 1, 25.0);
    }

    @Test
    void retainsLastPandaStandingsWhenOracleFails() {
        ProviderSyncStateRepository stateRepository = mock(ProviderSyncStateRepository.class);
        ProviderPlayerGameStatRepository statRepository = mock(ProviderPlayerGameStatRepository.class);
        when(stateRepository.findAll()).thenReturn(List.of(
                pandaState("SUCCESS", null),
                oracleState("FAILED", "Oracle unavailable")));
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(List.of(stat()));
        LecLiveDataService service = new LecLiveDataService(
                stateRepository,
                statRepository,
                new LecDataParser(new GameScoreCalculator()),
                new ObjectMapper());

        LecDataSnapshot snapshot = service.current();

        assertThat(snapshot.status()).isEqualTo("stale");
        assertThat(snapshot.standings()).extracting(LecDataSnapshot.Standing::teamName)
                .containsExactly("G2 Esports", "Fnatic");
    }

    private static ProviderSyncState pandaState(String status, String error) {
        return ProviderSyncState.builder()
                .provider(LecSynchronizationService.PANDASCORE)
                .status(status)
                .lastAttemptAt(Instant.parse("2026-07-28T12:00:00Z"))
                .lastSuccessAt(Instant.parse("2026-07-28T10:00:00Z"))
                .lastError(error)
                .providerSnapshot("""
                        [{"status":"finished","winner_id":1,
                          "opponents":[
                            {"opponent":{"id":1,"name":"G2 Esports"}},
                            {"opponent":{"id":2,"name":"Fnatic"}}]}]
                        """)
                .build();
    }

    private static ProviderSyncState oracleState(String status, String error) {
        return ProviderSyncState.builder()
                .provider(LecSynchronizationService.ORACLES_ELIXIR)
                .status(status)
                .lastAttemptAt(Instant.parse("2026-07-28T12:00:00Z"))
                .lastSuccessAt(Instant.parse("2026-07-28T10:00:00Z"))
                .lastError(error)
                .build();
    }

    private static ProviderPlayerGameStat stat() {
        return ProviderPlayerGameStat.builder()
                .providerGame(ProviderGame.builder()
                        .externalGameId("GAME-1")
                        .playedAt(Instant.parse("2026-07-28T09:00:00Z"))
                        .build())
                .lecPlayer(LecPlayer.builder().id(7L).nickname("Caps").ruolo(PlayerRole.MID).build())
                .sourceNickname("Caps")
                .sourceTeamName("G2 Esports")
                .sourceRole(PlayerRole.MID)
                .sourceChampion("Azir")
                .rawParticipated(true)
                .rawKills(4)
                .rawDeaths(2)
                .rawAssists(6)
                .rawCs(250)
                .rawVisionScore(20)
                .rawWin(true)
                .fantasyScore(25.0)
                .build();
    }
}
