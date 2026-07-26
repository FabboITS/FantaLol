package com.fantalol.backend.scoring;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.matchday.Matchday;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class FantasyTeamPointsTest {

    @Test
    void separatesConfirmedAndProvisionalPointsWithoutDoubleCounting() {
        FormationRepository formations = mock(FormationRepository.class);
        FantaTeamRepository teams = mock(FantaTeamRepository.class);
        MatchdayScoringEngine engine = new MatchdayScoringEngine(
                mock(MatchdaySeriesRepository.class), mock(OfficialGameRepository.class),
                mock(PlayerGameStatRepository.class), formations, teams, new GameScoreCalculator());
        FantaTeam team = FantaTeam.builder().id(7L).punti(8.0).build();
        Formation closed = formation(team, true, 4.5);
        Formation open = formation(team, false, 3.5);
        when(formations.findByFantaTeamId(7L)).thenReturn(List.of(closed, open));

        engine.recomputeTeamTotal(team);
        engine.recomputeTeamTotal(team);

        assertThat(team.getLegacyPoints()).isEqualTo(8.0);
        assertThat(team.getConfirmedPoints()).isEqualTo(12.5);
        assertThat(team.getProvisionalPoints()).isEqualTo(3.5);
        assertThat(team.getPunti()).isEqualTo(16.0);
        verify(teams, times(2)).save(team);
    }

    private static Formation formation(FantaTeam team, boolean closed, double score) {
        Matchday day = Matchday.builder().id(closed ? 1L : 2L).numero(closed ? 1 : 2).chiusa(closed).build();
        return Formation.builder().fantaTeam(team).matchday(day).punteggioTotale(score)
                .formulaVersion(RoleScoreWeights.FORMULA_VERSION).build();
    }
}
