package com.fantalol.backend.matchday;

import com.fantalol.backend.matchday.dto.LineupWindowResponse;
import com.fantalol.backend.security.JwtAuthFilter;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(FormationController.class)
class FormationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private FormationService formationService;

    @MockBean
    private JwtAuthFilter jwtAuthFilter;

    @Test
    @WithMockUser(username = "mago")
    void returnsTheStandaloneWindowForAnAuthenticatedOwner() throws Exception {
        when(formationService.lineupWindow("mago", 7L)).thenReturn(
                new LineupWindowResponse(true, Instant.parse("2026-07-31T22:00:00Z"), "open"));

        mockMvc.perform(get("/api/fanta-teams/7/formazioni/window"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.editable").value(true))
                .andExpect(jsonPath("$.nextEffectiveAt").value("2026-07-31T22:00:00Z"));
    }

    @Test
    void rejectsAnUnauthenticatedStandaloneWindowRequest() throws Exception {
        mockMvc.perform(get("/api/fanta-teams/7/formazioni/window"))
                .andExpect(status().isUnauthorized());
    }
}
