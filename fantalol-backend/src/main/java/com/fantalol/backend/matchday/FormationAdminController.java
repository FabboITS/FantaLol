package com.fantalol.backend.matchday;

import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/leagues/{leagueId}/matchdays/{matchdayId}/formations")
@RequiredArgsConstructor
public class FormationAdminController {

    private final FormationService formationService;

    @PostMapping("/confirm-all")
    @PreAuthorize("hasRole('ADMIN')")
    public FormationBulkConfirmationResponse confirmAll(
            org.springframework.security.core.Authentication authentication,
            @PathVariable Long leagueId,
            @PathVariable Long matchdayId) {
        int confirmed = formationService.confirmAllFormations(authentication.getName(), leagueId, matchdayId);
        return new FormationBulkConfirmationResponse(confirmed);
    }

    public record FormationBulkConfirmationResponse(int confirmedTeams) {
    }
}
