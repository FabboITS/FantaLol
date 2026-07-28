package com.fantalol.backend.matchday;

import com.fantalol.backend.matchday.dto.LineupRequest;
import com.fantalol.backend.matchday.dto.LineupResponse;
import com.fantalol.backend.matchday.dto.LineupWindowResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class FormationControllerTest {

    @Mock
    private FormationService formationService;
    @Mock
    private Authentication authentication;

    private FormationController controller;

    @BeforeEach
    void setUp() {
        controller = new FormationController(formationService);
    }

    @Test
    void returnsTheStandaloneWindowForTheAuthenticatedPrincipal() {
        Instant effectiveAt = Instant.parse("2026-07-31T22:00:00Z");
        when(authentication.getName()).thenReturn("mago");
        when(formationService.lineupWindow("mago", 7L)).thenReturn(
                new LineupWindowResponse(true, effectiveAt, "open"));

        LineupWindowResponse response = controller.window(authentication, 7L);

        assertThat(response.editable()).isTrue();
        assertThat(response.nextEffectiveAt()).isEqualTo(effectiveAt);
        assertThat(response.reason()).isEqualTo("open");
    }

    @Test
    void returnsTheMatchdayIndependentLineupForTheAuthenticatedPrincipal() {
        LineupResponse expected = new LineupResponse(List.of(), List.of(), true,
                Instant.parse("2026-07-30T22:00:00Z"));
        when(authentication.getName()).thenReturn("mago");
        when(formationService.findLineup("mago", 7L)).thenReturn(expected);

        assertThat(controller.lineup(authentication, 7L)).isSameAs(expected);
    }

    @Test
    void schedulesTheMatchdayIndependentLineupForTheAuthenticatedPrincipal() {
        LineupRequest request = new LineupRequest(List.of(11L, 12L, 13L, 14L, 15L));
        LineupResponse expected = new LineupResponse(List.of(), List.of(), true,
                Instant.parse("2026-07-30T22:00:00Z"));
        when(authentication.getName()).thenReturn("admin");
        when(formationService.scheduleLineup("admin", 7L, request)).thenReturn(expected);

        assertThat(controller.scheduleLineup(authentication, 7L, request)).isSameAs(expected);
    }
}
