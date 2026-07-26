package com.fantalol.backend.scoring;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecTeam;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class LecInsightsServiceTest {

    @Test
    void ranksTeamsAndPlayersWithTheVersionedFantasyFormula() {
        PlayerGameStatRepository stats = mock(PlayerGameStatRepository.class);
        OfficialGameRepository games = mock(OfficialGameRepository.class);
        LecInsightsService service = new LecInsightsService(stats, games, new GameScoreCalculator());
        LecTeam team = LecTeam.builder().nome("G2 Esports").logoUrl("/g2.png").build();
        LecPlayer top = LecPlayer.builder().id(1L).nickname("Top").ruolo(PlayerRole.TOP).team(team).build();
        LecPlayer support = LecPlayer.builder().id(2L).nickname("Support").ruolo(PlayerRole.SUPPORT).team(team).build();
        OfficialSeries series = OfficialSeries.builder().id(4L).provider("TEST").externalId("s1").completed(true).build();
        OfficialGame game = OfficialGame.builder().id(8L).series(series).provider("TEST")
                .externalId("g1").gameNumber(1).playedAt(Instant.parse("2026-07-01T18:00:00Z")).build();
        PlayerGameStat topStat = stat(game, top, 1, 0, 0, 0, false);
        PlayerGameStat supportStat = stat(game, support, 0, 0, 2, 0, false);
        when(stats.findAll()).thenReturn(List.of(topStat, supportStat));
        when(games.findAll()).thenReturn(List.of(game));
        when(stats.countByGameIdAndEffectiveSourceIsNotNull(8L)).thenReturn(10L);

        var response = service.summer2026();

        assertThat(response.dataStatus()).isEqualTo("COMPLETE");
        assertThat(response.standings()).singleElement().satisfies(row -> {
            assertThat(row.teamName()).isEqualTo("G2 Esports");
            assertThat(row.totalScore()).isEqualTo(1.6);
        });
        assertThat(response.players()).extracting(row -> row.nickname())
                .containsExactly("Support", "Top");
    }

    private static PlayerGameStat stat(OfficialGame game, LecPlayer player, int kills, int deaths,
                                       int assists, int cs, boolean win) {
        PlayerGameStat stat = PlayerGameStat.builder().game(game).player(player)
                .teamNameSnapshot("G2 Esports").build();
        stat.submit(StatSource.ORACLE, kills, deaths, assists, cs, win, "test");
        return stat;
    }
}
