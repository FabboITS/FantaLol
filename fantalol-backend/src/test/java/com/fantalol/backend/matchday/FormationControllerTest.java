package com.fantalol.backend.matchday;

import com.fantalol.backend.matchday.dto.LineupWindowResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;

import java.time.Instant;

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
}
