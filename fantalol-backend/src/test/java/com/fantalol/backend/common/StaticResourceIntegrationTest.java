package com.fantalol.backend.common;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
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
    void homeUsesFantaLeagueBrandAndPlayerHeroImages() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("<title>FantaLeague")))
                .andExpect(content().string(containsString("aria-label=\"FantaLeague home\"")))
                .andExpect(content().string(containsString("FANTA<span>LEAGUE</span>")))
                .andExpect(content().string(containsString("src=\"/Player_immage/Mid/Caps.jpg\"")))
                .andExpect(content().string(containsString("alt=\"Caps, mid laner for G2 Esports\"")))
                .andExpect(content().string(containsString("src=\"/Player_immage/Jungle/SkewMond.jpg\"")))
                .andExpect(content().string(containsString("alt=\"SkewMond, jungler\"")));
    }

    @Test
    void mainStylesheetUsesBlueVioletTheme() throws Exception {
        mockMvc.perform(get("/css/style.css"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("--lime:#4f8cff")))
                .andExpect(content().string(containsString("--violet:#8b5cf6")))
                .andExpect(content().string(containsString(".hero-player-image")))
                .andExpect(content().string(containsString("linear-gradient")))
                .andExpect(content().string(not(containsString("#c7ff37"))))
                .andExpect(content().string(not(containsString("#d6ff6b"))));
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

    @Test
    void homeContainsTheAdminUserDirectory() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("id=\"user-directory-dialog\"")))
                .andExpect(content().string(containsString("id=\"user-directory-list\"")));
    }

    @Test
    void loginDialogDoesNotExposeOrPrefillAdministratorCredentials() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(not(containsString("Demo " + "admin"))))
                .andExpect(content().string(not(containsString("name=\"username\" value="))))
                .andExpect(content().string(not(containsString("name=\"password\" value="))));
    }

    @Test
    void javascriptHandlesTheAdminShortcut() throws Exception {
        mockMvc.perform(get("/js/app.js"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("openUserDirectory")))
                .andExpect(content().string(containsString("event.ctrlKey")))
                .andExpect(content().string(containsString("state.user?.role!=='ADMIN'")))
                .andExpect(content().string(containsString("api('/users')")));
    }

    @Test
    void frontendContainsLeagueAuctionControlsAndAutomaticRefresh() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("id=\"auction-phase-controls\"")));

        mockMvc.perform(get("/js/app.js"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("/auction/${button.dataset.auctionPhase}")))
                .andExpect(content().string(containsString("/rosters/complete-randomly")))
                .andExpect(content().string(containsString("Non hai abbastanza crediti per rilanciare")))
                .andExpect(content().string(containsString("refreshAfterAuctionEnded")))
                .andExpect(content().string(containsString("await loadPrivateData()")));
    }
}
