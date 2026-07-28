package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.integration.lec.ProviderSyncState;
import com.fantalol.backend.integration.lec.ProviderSyncStateRepository;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.BrokenBarrierException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class OracleGameImportServiceTest {
    private final ProviderGameRepository providerGameRepository = mock(ProviderGameRepository.class);
    private final ProviderPlayerGameStatRepository playerGameStatRepository = mock(ProviderPlayerGameStatRepository.class);
    private final LecPlayerRepository lecPlayerRepository = mock(LecPlayerRepository.class);
    private final ProviderSyncStateRepository providerSyncStateRepository = mock(ProviderSyncStateRepository.class);
    private final Map<String, ProviderGame> games = new LinkedHashMap<>();
    private final Map<Long, ProviderPlayerGameStat> stats = new LinkedHashMap<>();
    private final Map<String, LecPlayer> players = new LinkedHashMap<>();
    private final Map<String, ProviderSyncState> syncStates = new LinkedHashMap<>();
    private OracleGameImportService service;
    private long nextStatId;

    @BeforeEach
    void setUp() {
        for (int index = 1; index <= 10; index++) {
            LecPlayer player = LecPlayer.builder()
                    .id((long) index)
                    .oraclePlayerId("player-" + index)
                    .nickname("Player " + index)
                    .build();
            players.put(player.getOraclePlayerId(), player);
        }

        when(lecPlayerRepository.findFirstByOraclePlayerIdIgnoreCase(any()))
                .thenAnswer(invocation -> Optional.ofNullable(players.get(invocation.getArgument(0))));
        when(lecPlayerRepository.findFirstByNicknameIgnoreCase(any()))
                .thenAnswer(invocation -> players.values().stream()
                        .filter(player -> player.getNickname().equalsIgnoreCase(invocation.getArgument(0)))
                        .findFirst());
        when(providerGameRepository.findByProviderAndExternalGameId(eq(ProviderGame.ORACLES_ELIXIR), any()))
                .thenAnswer(invocation -> Optional.ofNullable(games.get(invocation.getArgument(1))));
        when(providerGameRepository.save(any(ProviderGame.class))).thenAnswer(invocation -> {
            ProviderGame game = invocation.getArgument(0);
            if (game.getId() == null) {
                game.setId((long) games.size() + 1);
            }
            games.put(game.getExternalGameId(), game);
            return game;
        });
        when(playerGameStatRepository.findByProviderGameId(anyLong())).thenAnswer(invocation -> stats.values().stream()
                .filter(stat -> stat.getProviderGame().getId().equals(invocation.getArgument(0)))
                .toList());
        when(playerGameStatRepository.save(any(ProviderPlayerGameStat.class))).thenAnswer(invocation -> {
            ProviderPlayerGameStat stat = invocation.getArgument(0);
            if (stat.getId() == null) {
                ReflectionTestUtils.setField(stat, "id", ++nextStatId);
            }
            stats.put(stat.getId(), stat);
            return stat;
        });
        when(providerSyncStateRepository.findByProvider(any()))
                .thenAnswer(invocation -> Optional.ofNullable(syncStates.get(invocation.getArgument(0))));
        when(providerSyncStateRepository.save(any(ProviderSyncState.class))).thenAnswer(invocation -> {
            ProviderSyncState state = invocation.getArgument(0);
            syncStates.put(state.getProvider(), state);
            return state;
        });

        service = new OracleGameImportService(
                new OracleElixirGameParser(),
                providerGameRepository,
                playerGameStatRepository,
                lecPlayerRepository,
                new GameScoreCalculator(),
                providerSyncStateRepository);
    }

    @Test
    void insertsThenSkipsAnUnchangedCompleteGame() {
        String csv = csv(rows("GAME-1", "Player 1", 4));

        OracleImportSummary first = service.importCsv(csv, "LEC", "Summer");
        OracleImportSummary repeated = service.importCsv(csv, "LEC", "Summer");

        assertThat(first).extracting(OracleImportSummary::insertedGames, OracleImportSummary::updatedGames,
                        OracleImportSummary::skippedGames, OracleImportSummary::failedGames)
                .containsExactly(1, 0, 0, 0);
        assertThat(repeated).extracting(OracleImportSummary::insertedGames, OracleImportSummary::updatedGames,
                        OracleImportSummary::skippedGames, OracleImportSummary::failedGames)
                .containsExactly(0, 0, 1, 0);
        assertThat(games).hasSize(1);
        assertThat(stats).hasSize(10);
    }

    @Test
    void updatesProviderValuesAndFantasyScoreWhenTheGameFingerprintChanges() {
        service.importCsv(csv(rows("GAME-1", "Player 1", 4)), "LEC", "Summer");

        OracleImportSummary changed = service.importCsv(csv(rows("GAME-1", "Player 1", 9)), "LEC", "Summer");

        assertThat(changed).extracting(OracleImportSummary::insertedGames, OracleImportSummary::updatedGames,
                        OracleImportSummary::skippedGames, OracleImportSummary::failedGames)
                .containsExactly(0, 1, 0, 0);
        assertThat(stats.values()).filteredOn(stat -> stat.getLecPlayer().getId().equals(1L)).singleElement()
                .satisfies(stat -> {
                    assertThat(stat.getRawKills()).isEqualTo(9);
                    assertThat(stat.getFantasyScore()).isEqualTo(35.2625);
                });
    }

    @Test
    void rejectsTheEntireGameWhenOnePlayerCannotBeResolved() {
        String csv = csv(rows("GAME-1", "Unresolved", 4));

        OracleImportSummary result = service.importCsv(csv, "LEC", "Summer");

        assertThat(result).extracting(OracleImportSummary::insertedGames, OracleImportSummary::updatedGames,
                        OracleImportSummary::skippedGames, OracleImportSummary::failedGames)
                .containsExactly(0, 0, 0, 1);
        assertThat(result.unmatchedPlayers()).containsExactly("Unresolved");
        assertThat(games).isEmpty();
        assertThat(stats).isEmpty();
    }

    @Test
    void keepsCorrectedValuesActiveWhileRefreshingAnOverriddenProviderRow() {
        service.importCsv(csv(rows("GAME-1", "Player 1", 4)), "LEC", "Summer");
        ProviderPlayerGameStat overridden = stats.values().stream()
                .filter(stat -> stat.getLecPlayer().getId().equals(1L))
                .findFirst()
                .orElseThrow();
        overridden.setOverridden(true);
        overridden.setCorrectedKills(2);
        overridden.setFantasyScore(12.0);

        service.importCsv(csv(rows("GAME-1", "Player 1", 9)), "LEC", "Summer");

        assertThat(overridden)
                .extracting(ProviderPlayerGameStat::getRawKills, ProviderPlayerGameStat::getCorrectedKills,
                        ProviderPlayerGameStat::getFantasyScore)
                .containsExactly(9, 2, 12.0);
    }

    @Test
    void recordsOracleSuccessWithoutChangingPandaScoreState() {
        ProviderSyncState pandaState = ProviderSyncState.builder()
                .provider("PANDASCORE")
                .status("SUCCESS")
                .lastAttemptAt(Instant.parse("2026-07-24T10:00:00Z"))
                .lastSuccessAt(Instant.parse("2026-07-24T10:00:00Z"))
                .build();
        syncStates.put(pandaState.getProvider(), pandaState);

        service.importCsv(csv(rows("GAME-1", "Player 1", 4)), "LEC", "Summer");

        assertThat(syncStates).containsKey(ProviderGame.ORACLES_ELIXIR);
        assertThat(syncStates.get(ProviderGame.ORACLES_ELIXIR))
                .extracting(ProviderSyncState::getStatus, ProviderSyncState::getLastError)
                .containsExactly("SUCCESS", null);
        assertThat(syncStates.get("PANDASCORE")).isSameAs(pandaState);
    }

    @Test
    void recordsOracleFailureWithoutChangingPandaScoreState() {
        ProviderSyncState pandaState = ProviderSyncState.builder()
                .provider("PANDASCORE")
                .status("SUCCESS")
                .lastAttemptAt(Instant.parse("2026-07-24T10:00:00Z"))
                .lastSuccessAt(Instant.parse("2026-07-24T10:00:00Z"))
                .build();
        syncStates.put(pandaState.getProvider(), pandaState);

        service.recordOracleFailure(new IllegalStateException("Oracle unavailable"));

        assertThat(syncStates.get(ProviderGame.ORACLES_ELIXIR))
                .extracting(ProviderSyncState::getStatus, ProviderSyncState::getLastError)
                .containsExactly("FAILED", "Oracle unavailable");
        assertThat(syncStates.get("PANDASCORE")).isSameAs(pandaState);
    }

    @Test
    void rejectsAGameWhenTwoProviderRowsResolveToTheSameLocalPlayer() {
        players.put("player-2", players.get("player-1"));

        OracleImportSummary result = service.importCsv(csv(rows("GAME-1", "Player 1", 4)), "LEC", "Summer");

        assertThat(result).extracting(OracleImportSummary::insertedGames, OracleImportSummary::failedGames)
                .containsExactly(0, 1);
        assertThat(result.unmatchedPlayers()).containsExactly("Player 2");
        assertThat(games).isEmpty();
        assertThat(stats).isEmpty();
    }

    @Test
    void serializesConcurrentIdenticalImportsIntoOneInsertAndOneSkip() throws Exception {
        CyclicBarrier concurrentLookups = new CyclicBarrier(2);
        when(providerGameRepository.findByProviderAndExternalGameId(eq(ProviderGame.ORACLES_ELIXIR), any()))
                .thenAnswer(invocation -> {
                    try {
                        concurrentLookups.await(250, TimeUnit.MILLISECONDS);
                    } catch (BrokenBarrierException | java.util.concurrent.TimeoutException ignored) {
                        // A serialized caller is expected to time out here before the later lookup observes its game.
                    }
                    return Optional.ofNullable(games.get(invocation.getArgument(1)));
                });
        ExecutorService executor = Executors.newFixedThreadPool(2);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        try {
            Future<OracleImportSummary> first = executor.submit(() -> importAfterStarting(ready, start));
            Future<OracleImportSummary> second = executor.submit(() -> importAfterStarting(ready, start));
            assertThat(ready.await(1, TimeUnit.SECONDS)).isTrue();
            start.countDown();

            List<OracleImportSummary> summaries = List.of(
                    first.get(2, TimeUnit.SECONDS),
                    second.get(2, TimeUnit.SECONDS));

            assertThat(summaries).extracting(OracleImportSummary::insertedGames).containsExactlyInAnyOrder(1, 0);
            assertThat(summaries).extracting(OracleImportSummary::skippedGames).containsExactlyInAnyOrder(0, 1);
            assertThat(games).hasSize(1);
            assertThat(stats).hasSize(10);
            assertThat(syncStates.get(ProviderGame.ORACLES_ELIXIR))
                    .extracting(ProviderSyncState::getStatus, ProviderSyncState::getLastError)
                    .containsExactly("SUCCESS", null);
        } finally {
            executor.shutdownNow();
        }
    }

    private OracleImportSummary importAfterStarting(CountDownLatch ready, CountDownLatch start)
            throws InterruptedException {
        ready.countDown();
        assertThat(start.await(1, TimeUnit.SECONDS)).isTrue();
        return service.importCsv(csv(rows("GAME-1", "Player 1", 4)), "LEC", "Summer");
    }

    private static String csv(List<String> rows) {
        return "gameid,date,league,split,datacompleteness,playerid,playername,teamname,position,champion,kills,deaths,assists,total cs,visionscore,result\n"
                + String.join("\n", rows);
    }

    private static List<String> rows(String gameId, String firstPlayerName, int firstPlayerKills) {
        List<String> rows = new ArrayList<>();
        String[] positions = {"top", "jng", "mid", "bot", "sup", "top", "jng", "mid", "bot", "sup"};
        for (int index = 1; index <= 10; index++) {
            String playerName = index == 1 ? firstPlayerName : "Player " + index;
            String playerId = index == 1 && "Unresolved".equals(firstPlayerName) ? "unresolved-player" : "player-" + index;
            int kills = index == 1 ? firstPlayerKills : index;
            rows.add(String.join(",", gameId, "2026-07-24T16:00:00Z", "LEC", "Summer", "complete",
                    playerId, playerName, index <= 5 ? "Team A" : "Team B", positions[index - 1],
                    "Champion " + index, String.valueOf(kills), String.valueOf(index - 1), String.valueOf(index + 1),
                    String.valueOf(100 + index), String.valueOf(10 + index), index <= 5 ? "1" : "0"));
        }
        return rows;
    }
}
