package com.fantalol.backend.scoring;

import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.matchday.Matchday;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class MatchdayScoringEngineTest {
    private MatchdaySeriesRepository linkRepository;
    private PlayerGameStatRepository statRepository;
    private MatchdayScoringEngine engine;

    @BeforeEach
    void setUp() {
        linkRepository = mock(MatchdaySeriesRepository.class);
        statRepository = mock(PlayerGameStatRepository.class);
        engine = new MatchdayScoringEngine(linkRepository, mock(OfficialGameRepository.class),
                statRepository, mock(FormationRepository.class), mock(FantaTeamRepository.class),
                new GameScoreCalculator());
    }

    @Test
    void averagesOnlyAppearancesWithinEachSeriesThenSumsSeries() {
        LecPlayer player = LecPlayer.builder().id(9L).nickname("Test").ruolo(PlayerRole.MID).build();
        OfficialSeries first = OfficialSeries.builder().id(101L).provider("TEST").externalId("s1").build();
        OfficialSeries second = OfficialSeries.builder().id(102L).provider("TEST").externalId("s2").build();
        Matchday day = Matchday.builder().id(5L).numero(1).build();
        when(linkRepository.findByMatchdayId(5L)).thenReturn(List.of(
                MatchdaySeries.builder().matchday(day).series(first).build(),
                MatchdaySeries.builder().matchday(day).series(second).build()));
        when(statRepository.findByGameSeriesIdAndPlayerId(101L, 9L)).thenReturn(List.of(
                oracleStat(player, first, 1L, 1, 0, 0, 0, false),
                oracleStat(player, first, 2L, 3, 0, 0, 0, false)));
        when(statRepository.findByGameSeriesIdAndPlayerId(102L, 9L)).thenReturn(List.of(
                oracleStat(player, second, 3L, 2, 0, 0, 0, false)));

        // First series: average of 3 and 9 = 6. Second series: 6. Matchday: 12.
        assertThat(engine.playerMatchdayScore(5L, 9L)).isEqualTo(12.0);
    }

    private static PlayerGameStat oracleStat(LecPlayer player, OfficialSeries series, long gameId,
                                             int kills, int deaths, int assists, int cs, boolean win) {
        OfficialGame game = OfficialGame.builder().id(gameId).series(series)
                .provider("TEST").externalId("g" + gameId).gameNumber((int) gameId).build();
        PlayerGameStat stat = PlayerGameStat.builder().game(game).player(player).build();
        stat.submit(StatSource.ORACLE, kills, deaths, assists, cs, win, "test");
        return stat;
    }
}
