package com.fantalol.backend.team;

import com.fantalol.backend.team.dto.LecPlayerRequest;
import com.fantalol.backend.team.dto.LecPlayerResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Endpoint per la consultazione (pubblica) e la gestione (ADMIN) dei player LEC.
 */
@RestController
@RequestMapping("/api/players")
@RequiredArgsConstructor
@Tag(name = "Player LEC", description = "Anagrafica dei giocatori professionisti LEC")
public class LecPlayerController {

    private final LecPlayerService lecPlayerService;

    @GetMapping
    public List<LecPlayerResponse> findAll(@RequestParam(required = false) PlayerRole ruolo,
                                            @RequestParam(required = false) Long teamId) {
        return lecPlayerService.findAll(ruolo, teamId);
    }

    @GetMapping("/{id}")
    public LecPlayerResponse findById(@PathVariable Long id) {
        return lecPlayerService.findById(id);
    }

    @PostMapping
    public ResponseEntity<LecPlayerResponse> create(@Valid @RequestBody LecPlayerRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(lecPlayerService.create(request));
    }

    @PutMapping("/{id}")
    public LecPlayerResponse update(@PathVariable Long id, @Valid @RequestBody LecPlayerRequest request) {
        return lecPlayerService.update(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        lecPlayerService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
