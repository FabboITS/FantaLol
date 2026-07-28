package com.fantalol.backend.scoring;

import com.fantalol.backend.league.FantaTeamService;
import com.fantalol.backend.league.LeagueService;
import com.fantalol.backend.scoring.dto.CumulativeDataResponse;
import com.fantalol.backend.scoring.dto.CumulativeFantasyTeamScore;
import com.fantalol.backend.scoring.dto.CumulativePlayerScore;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CumulativeScoringControllerTest {

    private final CumulativeScoringService scoringService = mock(CumulativeScoringService.class);
    private final FantaTeamService fantaTeamService = mock(FantaTeamService.class);
    private final LeagueService leagueService = mock(LeagueService.class);
    private final CumulativeDataFreshnessService freshnessService = mock(CumulativeDataFreshnessService.class);
    private final CumulativeScoringController controller = new CumulativeScoringController(
            scoringService, fantaTeamService, leagueService, freshnessService);

    @Test
    void publicPlayerScoresIncludeSanitizedSourceFreshness() {
        var scores = List.of(new CumulativePlayerScore(4L, "Caps", PlayerRole.MID, 3, 18.5, "available"));
        var wrapped = new CumulativeDataResponse<>("stale", Instant.parse("2026-07-28T12:00:00Z"), true, scores);
        when(scoringService.playerScores()).thenReturn(scores);
        when(freshnessService.wrap(scores)).thenReturn(wrapped);

        CumulativeDataResponse<CumulativePlayerScore> response = controller.playerScores();

        assertThat(response).isSameAs(wrapped);
    }

    @Test
    void leagueRankingKeepsMembershipCheckAndWrapsTeamScores() {
        var scores = List.of(new CumulativeFantasyTeamScore(7L, "Mago", List.of(), 21.25, false));
        var wrapped = new CumulativeDataResponse<>("fresh", Instant.parse("2026-07-28T14:00:00Z"), false, scores);
        when(scoringService.leagueRanking(3L)).thenReturn(scores);
        when(freshnessService.wrap(scores)).thenReturn(wrapped);
        var authentication = new UsernamePasswordAuthenticationToken("mago", "ignored");

        CumulativeDataResponse<CumulativeFantasyTeamScore> response =
                controller.leagueRanking(authentication, 3L);

        assertThat(response).isSameAs(wrapped);
        verify(leagueService).findById("mago", 3L);
    }
}
