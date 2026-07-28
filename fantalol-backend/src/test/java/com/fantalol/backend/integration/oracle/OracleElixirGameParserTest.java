package com.fantalol.backend.integration.oracle;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class OracleElixirGameParserTest {
    private final OracleElixirGameParser parser = new OracleElixirGameParser();

    @Test
    void parsesOneCompleteLecSummerGameWithTenPlayerRows() {
        List<OracleGameBatch> games = parser.parse(csv(validPlayerRows()), "LEC", "Summer");

        assertThat(games).singleElement().satisfies(game -> {
            assertThat(game.externalGameId()).isEqualTo("LEC_2026_001");
            assertThat(game.playedAt()).isEqualTo(Instant.parse("2026-07-24T16:00:00Z"));
            assertThat(game.players()).hasSize(10);
            assertThat(game.players().get(0))
                    .extracting(OraclePlayerGameRow::externalPlayerId,
                            OraclePlayerGameRow::nickname,
                            OraclePlayerGameRow::teamName,
                            OraclePlayerGameRow::champion,
                            OraclePlayerGameRow::kills,
                            OraclePlayerGameRow::deaths,
                            OraclePlayerGameRow::assists,
                            OraclePlayerGameRow::cs,
                            OraclePlayerGameRow::visionScore,
                            OraclePlayerGameRow::win)
                    .containsExactly("player-1", "Player 1", "Team A", "Champion 1", 1, 0, 2, 101, 11, true);
        });
    }

    @Test
    void excludesRowsOutsideTheRequestedCompletePlayerGameData() {
        String excludedRows = String.join("\n",
                row("LEC_2026_SPRING", "2026-07-24T16:00:00Z", "LEC", "Spring", "complete", "spring-player", "Spring", "Team A", "mid", "Ahri", 1, 1, 1, 100, 10, 1),
                row("LEC_2026_INCOMPLETE", "2026-07-24T16:00:00Z", "LEC", "Summer", "partial", "incomplete-player", "Incomplete", "Team A", "mid", "Ahri", 1, 1, 1, 100, 10, 1),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "team-summary", "Team A", "Team A", "team", "", 10, 5, 20, 1000, 100, 1),
                row("", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "blank-game", "Blank", "Team A", "mid", "Ahri", 1, 1, 1, 100, 10, 1));

        List<OracleGameBatch> games = parser.parse(csv(validPlayerRows()) + "\n" + excludedRows, "LEC", "Summer");

        assertThat(games).singleElement().satisfies(game -> assertThat(game.players()).hasSize(10));
    }

    @Test
    void createsTheSameFingerprintWhenEquivalentRowsArriveInDifferentOrder() {
        List<String> rows = validPlayerRows();
        List<String> reversedRows = new ArrayList<>(rows);
        Collections.reverse(reversedRows);

        OracleGameBatch original = parser.parse(csv(rows), "LEC", "Summer").get(0);
        OracleGameBatch reordered = parser.parse(csv(reversedRows), "LEC", "Summer").get(0);

        assertThat(reordered.sourceFingerprint()).isEqualTo(original.sourceFingerprint());
    }

    private static String csv(List<String> rows) {
        return "gameid,date,league,split,datacompleteness,playerid,playername,teamname,position,champion,kills,deaths,assists,total cs,visionscore,result\n"
                + String.join("\n", rows);
    }

    private static List<String> validPlayerRows() {
        return List.of(
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-1", "Player 1", "Team A", "top", "Champion 1", 1, 0, 2, 101, 11, 1),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-2", "Player 2", "Team A", "jng", "Champion 2", 2, 1, 3, 102, 12, 1),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-3", "Player 3", "Team A", "mid", "Champion 3", 3, 2, 4, 103, 13, 1),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-4", "Player 4", "Team A", "bot", "Champion 4", 4, 3, 5, 104, 14, 1),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-5", "Player 5", "Team A", "sup", "Champion 5", 5, 4, 6, 105, 15, 1),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-6", "Player 6", "Team B", "top", "Champion 6", 6, 5, 7, 106, 16, 0),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-7", "Player 7", "Team B", "jng", "Champion 7", 7, 6, 8, 107, 17, 0),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-8", "Player 8", "Team B", "mid", "Champion 8", 8, 7, 9, 108, 18, 0),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-9", "Player 9", "Team B", "bot", "Champion 9", 9, 8, 10, 109, 19, 0),
                row("LEC_2026_001", "2026-07-24T16:00:00Z", "LEC", "Summer", "complete", "player-10", "Player 10", "Team B", "sup", "Champion 10", 10, 9, 11, 110, 20, 0));
    }

    private static String row(String gameId, String date, String league, String split, String completeness,
                              String playerId, String playerName, String teamName, String position, String champion,
                              int kills, int deaths, int assists, int cs, int visionScore, int result) {
        return String.join(",", gameId, date, league, split, completeness, playerId, playerName, teamName, position,
                champion, String.valueOf(kills), String.valueOf(deaths), String.valueOf(assists), String.valueOf(cs),
                String.valueOf(visionScore), String.valueOf(result));
    }
}
