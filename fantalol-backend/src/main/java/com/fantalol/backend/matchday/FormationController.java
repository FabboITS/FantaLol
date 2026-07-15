package com.fantalol.backend.matchday;

import com.fantalol.backend.matchday.dto.FormationRequest;
import com.fantalol.backend.matchday.dto.FormationResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

/**
 * Endpoint per la gestione della formazione schierata da una FantaTeam per una giornata.
 * Richiede autenticazione: solo il proprietario della squadra può modificarla.
 */
@RestController
@RequestMapping("/api/fanta-teams/{fantaTeamId}/formazioni")
@RequiredArgsConstructor
@Tag(name = "Formazioni", description = "Gestione della formazione (titolari e capitano) per giornata")
public class FormationController {

    private final FormationService formationService;

    @GetMapping("/{matchdayId}")
    public FormationResponse findByMatchday(@PathVariable Long fantaTeamId, @PathVariable Long matchdayId) {
        return formationService.findByTeamAndMatchday(fantaTeamId, matchdayId);
    }

    @PutMapping
    public FormationResponse imposta(Authentication authentication,
                                      @PathVariable Long fantaTeamId,
                                      @Valid @RequestBody FormationRequest request) {
        return formationService.impostaFormazione(authentication.getName(), fantaTeamId, request);
    }
}
