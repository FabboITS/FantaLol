package com.fantalol.backend.scoring;

import com.fantalol.backend.league.LeagueService;
import com.fantalol.backend.scoring.dto.CumulativeDataResponse;
import com.fantalol.backend.scoring.dto.CumulativeFantasyTeamScore;
import com.fantalol.backend.scoring.dto.CumulativePlayerScore;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;

import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class CumulativeScoringControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private CumulativeScoringService scoringService;

    @MockBean
    private CumulativeDataFreshnessService freshnessService;

    @MockBean
    private LeagueService leagueService;

    @Test
    void anonymousVisitorCanReadSanitizedCumulativePerformances() throws Exception {
        when(scoringService.playerScores()).thenReturn(List.of());
        when(freshnessService.<CumulativePlayerScore>wrap(anyList())).thenReturn(
                new CumulativeDataResponse<>("stale", Instant.parse("2026-07-28T12:00:00Z"), true, List.of()));

        mockMvc.perform(get("/api/lec/cumulative-performances"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("stale"))
                .andExpect(jsonPath("$.lastUpdatedAt").value("2026-07-28T12:00:00Z"))
                .andExpect(jsonPath("$.provisional").value(true))
                .andExpect(jsonPath("$.items").isArray())
                .andExpect(jsonPath("$.lastError").doesNotExist())
                .andExpect(jsonPath("$.unmatchedPlayers").doesNotExist())
                .andExpect(jsonPath("$.providerSnapshot").doesNotExist())
                .andExpect(jsonPath("$.failedGames").doesNotExist());
    }

    @Test
    void anonymousVisitorCannotReadPrivateLeagueRanking() throws Exception {
        mockMvc.perform(get("/api/leagues/3/cumulative-ranking"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "mago", roles = "USER")
    void authenticatedLeagueMemberReceivesSanitizedRankingFreshness() throws Exception {
        when(scoringService.leagueRanking(3L)).thenReturn(List.of());
        when(freshnessService.<CumulativeFantasyTeamScore>wrap(anyList())).thenReturn(
                new CumulativeDataResponse<>("fresh", Instant.parse("2026-07-28T14:00:00Z"), false, List.of()));

        mockMvc.perform(get("/api/leagues/3/cumulative-ranking"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("fresh"))
                .andExpect(jsonPath("$.lastUpdatedAt").value("2026-07-28T14:00:00Z"))
                .andExpect(jsonPath("$.provisional").value(false))
                .andExpect(jsonPath("$.items").isArray())
                .andExpect(jsonPath("$.lastError").doesNotExist())
                .andExpect(jsonPath("$.unmatchedPlayers").doesNotExist());

        verify(leagueService).findById("mago", 3L);
    }
}
