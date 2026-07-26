package com.fantalol.backend.common;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
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
                .andExpect(content().string(containsString("src=\"/Player_immage/other/Caps_1.webp\"")))
                .andExpect(content().string(containsString("alt=\"Caps, mid laner for G2 Esports\"")))
                .andExpect(content().string(containsString("src=\"/Player_immage/other/BB_1.webp\"")))
                .andExpect(content().string(containsString("alt=\"BrokenBlade, top laner\"")));
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
    void rulesTriggerIsAFullSizeSecondaryButton() throws Exception {
        mockMvc.perform(get("/css/style.css"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString(".rules-trigger")))
                .andExpect(content().string(containsString("width:100%")))
                .andExpect(content().string(containsString("min-height:45px")))
                .andExpect(content().string(containsString("border:1px solid var(--lime)")));
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
    void homeOrdersLeaguesBeforePlayersInNavigationAndContent() throws Exception {
        String html = mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();

        assertThat(html.indexOf("href=\"#leagues\""))
                .isLessThan(html.indexOf("href=\"#players\""));
        assertThat(html.indexOf("id=\"leagues\""))
                .isLessThan(html.indexOf("id=\"players\""));
    }

    @Test
    void frontendSupportsAdminLeagueDeletionAndUserEmailDirectory() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("Scorciatoia: Ctrl+Y")));

        mockMvc.perform(get("/js/app.js"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("event.code==='KeyY'")))
                .andExpect(content().string(containsString("user.email")))
                .andExpect(content().string(containsString("canDeleteLeague")))
                .andExpect(content().string(containsString("data-delete-league")))
                .andExpect(content().string(containsString("method:'DELETE'")))
                .andExpect(content().string(containsString("confirm(")));
    }

    @Test
    void homeContainsCompleteRulesDialogAndLeagueDetailNavigation() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("id=\"rules-button\"")))
                .andExpect(content().string(containsString("id=\"rules-dialog\"")))
                .andExpect(content().string(containsString("Regole FantaLeague LEC")))
                .andExpect(content().string(containsString("Cambi nei roster reali")))
                .andExpect(content().string(containsString("media delle sole partite disputate")))
                .andExpect(content().string(containsString("0 punti")))
                .andExpect(content().string(containsString("Accettazione delle regole")));

        mockMvc.perform(get("/js/app.js"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("/lega.html?id=${league.id}")))
                .andExpect(content().string(not(containsString("data-auction=\"${team.id}\""))))
                .andExpect(content().string(not(containsString("data-matchday=\"${league.id}\""))));
    }

    @Test
    void servesLeagueDashboardAndItsIntegrationReadyAssets() throws Exception {
        mockMvc.perform(get("/lega.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("id=\"league-error\"")))
                .andExpect(content().string(containsString("data-section=\"overview\"")))
                .andExpect(content().string(containsString("data-section=\"teams\"")))
                .andExpect(content().string(containsString("data-section=\"auction\"")))
                .andExpect(content().string(containsString("data-section=\"matchdays\"")))
                .andExpect(content().string(containsString("data-section=\"lec\"")))
                .andExpect(content().string(containsString("data-section=\"performance\"")))
                .andExpect(content().string(containsString("id=\"auction-phase-controls\"")))
                .andExpect(content().string(containsString("id=\"formation-dialog\"")))
                .andExpect(content().string(containsString("id=\"roster-history\"")))
                .andExpect(content().string(not(containsString("name=\"capitanoId\""))))
                .andExpect(content().string(containsString("id=\"matchday-dialog\"")));

        for (String asset : List.of("/css/league-detail.css", "/js/league-utils.js",
                "/js/lec-data-source.js", "/js/league-detail.js")) {
            mockMvc.perform(get(asset)).andExpect(status().isOk());
        }

        mockMvc.perform(get("/js/lec-data-source.js"))
                .andExpect(content().string(containsString("status:'not-connected'")))
                .andExpect(content().string(not(containsString("position:"))));
    }

    @Test
    void frontendContainsLeagueAuctionControlsAndAutomaticRefresh() throws Exception {
        mockMvc.perform(get("/index.html"))
                .andExpect(status().isOk())
                .andExpect(content().string(not(containsString("id=\"auction-dialog\""))))
                .andExpect(content().string(not(containsString("id=\"formation-dialog\""))))
                .andExpect(content().string(not(containsString("id=\"matchday-dialog\""))));

        mockMvc.perform(get("/js/league-detail.js"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("/auction/${action}")))
                .andExpect(content().string(containsString("/rosters/complete-randomly")))
                .andExpect(content().string(containsString("/formazioni")))
                .andExpect(content().string(containsString("Modifica formazione")))
                .andExpect(content().string(containsString("Vedi la tua rosa")))
                .andExpect(content().string(containsString("matchdayScore")))
                .andExpect(content().string(not(containsString("capitanoId"))))
                .andExpect(content().string(containsString("api('/matchdays'")))
                .andExpect(content().string(containsString("Non hai abbastanza crediti per rilanciare")))
                .andExpect(content().string(containsString("setInterval(synchronizeLeaguePage,2000)")))
                .andExpect(content().string(containsString("setInterval(renderCountdown,100)")))
                .andExpect(content().string(containsString("Sei il miglior offerente")))
                .andExpect(content().string(containsString("timer a 15 secondi")))
                .andExpect(content().string(containsString("beforeunload")));
    }
}
