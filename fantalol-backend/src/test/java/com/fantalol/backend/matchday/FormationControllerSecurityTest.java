package com.fantalol.backend.matchday;

import com.fantalol.backend.matchday.dto.LineupResponse;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class FormationControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private FormationService formationService;

    @Test
    void anonymousUserCannotScheduleALineup() throws Exception {
        mockMvc.perform(put("/api/fanta-teams/7/formazioni/lineup")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"titolariIds\":[11,12,13,14,15]}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "mago", roles = "USER")
    void authenticatedManagerCanReachTheMatchdayIndependentLineupCommand() throws Exception {
        when(formationService.scheduleLineup(
                org.mockito.ArgumentMatchers.eq("mago"),
                org.mockito.ArgumentMatchers.eq(7L),
                org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LineupResponse(List.of(), List.of(), true,
                        Instant.parse("2026-07-30T22:00:00Z")));

        mockMvc.perform(put("/api/fanta-teams/7/formazioni/lineup")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"titolariIds\":[11,12,13,14,15]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.editable").value(true))
                .andExpect(jsonPath("$.nextEffectiveAt").value("2026-07-30T22:00:00Z"));

        verify(formationService).scheduleLineup(
                org.mockito.ArgumentMatchers.eq("mago"),
                org.mockito.ArgumentMatchers.eq(7L),
                org.mockito.ArgumentMatchers.any());
    }

    @Test
    @WithMockUser(username = "mago", roles = "USER")
    void regularUserCannotConfirmAllLeagueFormations() throws Exception {
        mockMvc.perform(post("/api/admin/leagues/1/matchdays/2/formations/confirm-all"))
                .andExpect(status().isForbidden());
    }

    @Test
    @WithMockUser(username = "admin", roles = "ADMIN")
    void adminCanConfirmAllLeagueFormations() throws Exception {
        when(formationService.confirmAllFormations("admin", 1L, 2L)).thenReturn(8);

        mockMvc.perform(post("/api/admin/leagues/1/matchdays/2/formations/confirm-all"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.confirmedTeams").value(8));

        verify(formationService).confirmAllFormations("admin", 1L, 2L);
    }
}
