package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.scoring.GameScoreCalculator;
import org.junit.jupiter.api.Test;

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
        assertThat(support.visionScore()).isEqualTo(87);
        assertThat(support.perfectKda()).isTrue();
        assertThat(support.kda()).isNull();
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
}
