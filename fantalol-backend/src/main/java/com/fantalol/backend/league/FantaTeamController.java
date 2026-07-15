package com.fantalol.backend.league;

import com.fantalol.backend.league.dto.*;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Endpoint per l'iscrizione a una lega, la consultazione delle proprie squadre
 * e la gestione della rosa tramite asta a crediti.
 */
@RestController
@RequestMapping("/api/fanta-teams")
@RequiredArgsConstructor
@Tag(name = "Fanta Team & Asta", description = "Iscrizione alle leghe, rosa e asta a crediti")
public class FantaTeamController {

    private final FantaTeamService fantaTeamService;

    @PostMapping("/join")
    public ResponseEntity<FantaTeamResponse> joinLeague(Authentication authentication,
                                                         @Valid @RequestBody JoinLeagueRequest request) {
        FantaTeamResponse response = fantaTeamService.joinLeague(authentication.getName(), request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/me")
    public List<FantaTeamResponse> findMine(Authentication authentication) {
        return fantaTeamService.findMine(authentication.getName());
    }

    @GetMapping("/{id}")
    public FantaTeamResponse findById(@PathVariable Long id) {
        return fantaTeamService.findById(id);
    }

    @GetMapping("/by-league/{leagueId}")
    public List<FantaTeamResponse> findByLeague(@PathVariable Long leagueId) {
        return fantaTeamService.findByLeague(leagueId);
    }

    @PostMapping("/{id}/rosa/gratis")
    public ResponseEntity<RosterEntryResponse> acquistaPlayerGratis(Authentication authentication,
                                                                    @PathVariable Long id) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(fantaTeamService.acquistaPlayerGratis(authentication.getName(), id));
    }

    @PostMapping("/{id}/rosa/completa-casualmente")
    public FantaTeamResponse completaRosaCasualmente(Authentication authentication, @PathVariable Long id) {
        return fantaTeamService.completaRosaCasualmente(authentication.getName(), id);
    }

    @DeleteMapping("/{id}/rosa/{rosterEntryId}")
    public ResponseEntity<Void> rilasciaPlayer(Authentication authentication,
                                                @PathVariable Long id,
                                                @PathVariable Long rosterEntryId) {
        fantaTeamService.rilasciaPlayer(authentication.getName(), id, rosterEntryId);
        return ResponseEntity.noContent().build();
    }
}
