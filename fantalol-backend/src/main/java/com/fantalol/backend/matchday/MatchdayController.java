package com.fantalol.backend.matchday;

import com.fantalol.backend.matchday.dto.MatchdayRequest;
import com.fantalol.backend.matchday.dto.MatchdayResponse;
import com.fantalol.backend.matchday.dto.PlayerStatRequest;
import com.fantalol.backend.matchday.dto.PlayerStatResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Endpoint per la gestione delle giornate di campionato e delle statistiche dei player.
 * La consultazione è pubblica, l'inserimento/chiusura è riservata all'ADMIN (vedi SecurityConfig).
 */
@RestController
@RequestMapping("/api/matchdays")
@RequiredArgsConstructor
@Tag(name = "Giornate & Statistiche", description = "Gestione giornate di campionato e statistiche reali dei player")
public class MatchdayController {

    private final MatchdayService matchdayService;

    @GetMapping
    public List<MatchdayResponse> findAll() {
        return matchdayService.findAll();
    }

    @GetMapping("/{id}")
    public MatchdayResponse findById(@PathVariable Long id) {
        return matchdayService.findById(id);
    }

    @PostMapping
    public ResponseEntity<MatchdayResponse> create(Authentication authentication, @Valid @RequestBody MatchdayRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(matchdayService.create(authentication.getName(), request));
    }

    @GetMapping("/{id}/stats")
    public List<PlayerStatResponse> findStats(@PathVariable Long id) {
        return matchdayService.findStats(id);
    }

    @PostMapping("/{id}/stats")
    public ResponseEntity<PlayerStatResponse> inserisciStatistiche(Authentication authentication, @PathVariable Long id,
                                                                     @Valid @RequestBody PlayerStatRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(matchdayService.inserisciStatistiche(authentication.getName(), id, request));
    }

    @PostMapping("/{id}/chiudi")
    public MatchdayResponse chiudiGiornata(Authentication authentication, @PathVariable Long id) {
        return matchdayService.chiudiGiornata(authentication.getName(), id);
    }

    @PostMapping("/{id}/waiting-for-postponed")
    public MatchdayResponse markWaitingForPostponedMatches(Authentication authentication, @PathVariable Long id) {
        return matchdayService.markWaitingForPostponedMatches(authentication.getName(), id);
    }

    @PostMapping("/{id}/formation-lock")
    public MatchdayResponse lockFormations(Authentication authentication, @PathVariable Long id) {
        return matchdayService.setFormationLocked(authentication.getName(), id, true);
    }

    @DeleteMapping("/{id}/formation-lock")
    public MatchdayResponse unlockFormations(Authentication authentication, @PathVariable Long id) {
        return matchdayService.setFormationLocked(authentication.getName(), id, false);
    }
}
