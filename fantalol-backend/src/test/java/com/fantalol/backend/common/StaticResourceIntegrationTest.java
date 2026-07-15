package com.fantalol.backend.common;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class StaticResourceIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void servesTheFrontendFaviconWithoutAuthentication() throws Exception {
        mockMvc.perform(get("/favicon.svg"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("image/svg+xml"));
    }

    @Test
    void servesPlayerPortraitWithoutAuthentication() throws Exception {
        mockMvc.perform(get("/Player_immage/Mid/Caps.jpg"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("image/jpeg"));
    }

    @Test
    void servesTeamLogoWithoutAuthentication() throws Exception {
        mockMvc.perform(get("/assets/team-logos/g2-esports.png"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("image/png"));
    }

    @Test
    void portraitStylesheetShowsTheCompletePlayerImage() throws Exception {
        mockMvc.perform(get("/css/player-images.css"))
                .andExpect(status().isOk())
                .andExpect(content().string(org.hamcrest.Matchers.containsString("object-fit: contain")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("object-position: center bottom")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("max-height: 100%")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("max-width: 100%")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("min-width: 0")))
                .andExpect(content().string(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("background: linear-gradient"))));
    }

    @Test
    void missingStaticResourceReturnsNotFound() throws Exception {
        mockMvc.perform(get("/favicon.ico"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.path").value("/favicon.ico"));
    }
}
