package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.integration.oracle.ProviderGame;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class LecDataParserTest {
    private final LecDataParser parser = new LecDataParser(new GameScoreCalculator());
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void buildsStandingsPerformancesChampionPicksAndPerGameRows() throws Exception {
        String matches = """
                [{"id":10,"name":"G2 vs FNC","status":"finished","begin_at":"2026-07-26T18:00:00Z",
                  "winner_id":1,"opponents":[
                    {"opponent":{"id":1,"name":"G2 Esports"}},
                    {"opponent":{"id":2,"name":"Fnatic"}}]}]
                """;
        String csv = """
                gameid,league,split,datacompleteness,position,playerid,playername,teamname,champion,kills,deaths,assists,total cs,visionscore,result,date
                G10-1,LEC,Summer,complete,mid,caps,Caps,G2 Esports,Ahri,4,1,7,245,31,1,2026-07-26
                G10-1,LEC,Summer,complete,sup,mikyx,Mikyx,Fnatic,Rakan,0,0,8,32,87,0,2026-07-26
                """;

        LecDataSnapshot snapshot = parser.parse(objectMapper.readTree(matches), csv, "LEC", "Summer");

        assertThat(snapshot.standings()).extracting(LecDataSnapshot.Standing::teamName)
                .containsExactly("G2 Esports", "Fnatic");
        assertThat(snapshot.standings().get(0).seriesWins()).isEqualTo(1);
        assertThat(snapshot.performances()).extracting(LecDataSnapshot.PlayerPerformance::nickname)
                .contains("Caps", "Mikyx");
        assertThat(snapshot.performances().stream()
                .filter(player -> player.nickname().equals("Caps"))
                .findFirst().orElseThrow().champions().get(0).pickCount()).isEqualTo(1);
        LecDataSnapshot.GamePlayer support = snapshot.matches().get(0).games().get(0).players().stream()
                .filter(player -> player.nickname().equals("Mikyx"))
                .findFirst().orElseThrow();
        LecDataSnapshot.GamePlayer caps = snapshot.matches().get(0).games().get(0).players().stream()
                .filter(player -> player.nickname().equals("Caps"))
                .findFirst().orElseThrow();
        assertThat(support.visionScore()).isEqualTo(87);
        assertThat(support.perfectKda()).isTrue();
        assertThat(support.kda()).isNull();
        assertThat(caps.fantasyScore()).isEqualTo(4 * 3.0 + 7 * 2.0 - 1 * 2.0 + 245 / 100.0 + 3.0);
    }

    @Test
    void replacesSupportCsWithVisionWhenCalculatingFantasyAverage() throws Exception {
        String csv = """
                gameid,league,split,datacompleteness,position,playerid,playername,teamname,champion,kills,deaths,assists,total cs,visionscore,result,date
                G1,LEC,Summer,complete,sup,mikyx,Mikyx,Fnatic,Rakan,0,0,0,999,50,0,2026-07-26
                """;

        LecDataSnapshot snapshot = parser.parse(objectMapper.readTree("[]"), csv, "LEC", "Summer");

        assertThat(snapshot.performances().get(0).fantasyAverage()).isEqualTo(1.0);
    }

    @Test
    void persistedProjectionKeepsRemovedOverrideActiveUntilExplicitRestore() {
        ProviderPlayerGameStat current = persistedStat("Current", "current", "current");
        current.setRawParticipated(false);
        current.setCorrectedParticipated(true);
        ProviderPlayerGameStat stale = persistedStat("Former", "former", "current");
        stale.setOverridden(true);
        stale.setCorrectedParticipated(true);
        ProviderPlayerGameStat staleNonparticipant = persistedStat("Former Bench", "former", "current");
        staleNonparticipant.setOverridden(true);
        staleNonparticipant.setCorrectedParticipated(false);

        LecDataSnapshot snapshot = parser.project(
                objectMapper.createArrayNode(),
                List.of(current, stale, staleNonparticipant),
                "fresh",
                Instant.parse("2026-07-28T12:00:00Z"));

        assertThat(snapshot.performances())
                .extracting(LecDataSnapshot.PlayerPerformance::nickname)
                .containsExactly("Current", "Former");
        assertThat(snapshot.matches()).singleElement()
                .satisfies(match -> assertThat(match.games().get(0).players())
                        .extracting(LecDataSnapshot.GamePlayer::nickname)
                        .containsExactly("Current", "Former"));
    }

    private static ProviderPlayerGameStat persistedStat(
            String nickname,
            String statFingerprint,
            String gameFingerprint
    ) {
        return ProviderPlayerGameStat.builder()
                .providerGame(ProviderGame.builder()
                        .externalGameId("GAME-1")
                        .playedAt(Instant.parse("2026-07-28T09:00:00Z"))
                        .sourceFingerprint(gameFingerprint)
                        .build())
                .lecPlayer(LecPlayer.builder().id((long) nickname.hashCode()).nickname(nickname)
                        .ruolo(PlayerRole.MID).build())
                .sourceNickname(nickname)
                .sourceTeamName("G2 Esports")
                .sourceRole(PlayerRole.MID)
                .sourceChampion("Azir")
                .sourceFingerprint(statFingerprint)
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
