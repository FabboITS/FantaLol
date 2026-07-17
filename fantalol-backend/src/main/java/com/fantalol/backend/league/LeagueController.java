package com.fantalol.backend.league;

import com.fantalol.backend.league.dto.LeagueRequest;
import com.fantalol.backend.league.dto.LeagueResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Endpoint per la creazione e consultazione delle leghe private. Richiedono autenticazione.
 */
@RestController
@RequestMapping("/api/leagues")
@RequiredArgsConstructor
@Tag(name = "Leghe", description = "Creazione e consultazione delle leghe private")
public class LeagueController {

    private final LeagueService leagueService;

    @GetMapping
    public List<LeagueResponse> findAll() {
        return leagueService.findAll();
    }

    @GetMapping("/{id}")
    public LeagueResponse findById(@PathVariable Long id) {
        return leagueService.findById(id);
    }

    @PostMapping
    public ResponseEntity<LeagueResponse> create(Authentication authentication,
                                                  @Valid @RequestBody LeagueRequest request) {
        LeagueResponse response = leagueService.create(authentication.getName(), request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(Authentication authentication, @PathVariable Long id) {
        leagueService.delete(authentication.getName(), id);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/{id}/auction/open")
    public LeagueResponse openAuction(Authentication authentication, @PathVariable Long id) {
        return leagueService.openAuction(authentication.getName(), id);
    }

    @PutMapping("/{id}/auction/close")
    public LeagueResponse closeAuction(Authentication authentication, @PathVariable Long id) {
        return leagueService.closeAuction(authentication.getName(), id);
    }

    @PostMapping("/{id}/rosters/complete-randomly")
    public List<com.fantalol.backend.league.dto.FantaTeamResponse> completeAllRostersRandomly(
            Authentication authentication, @PathVariable Long id) {
        return leagueService.completeAllRostersRandomly(authentication.getName(), id);
    }
}
