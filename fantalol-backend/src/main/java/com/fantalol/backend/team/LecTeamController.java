package com.fantalol.backend.team;

import com.fantalol.backend.team.dto.LecTeamRequest;
import com.fantalol.backend.team.dto.LecTeamResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Endpoint per la consultazione (pubblica) e la gestione (ADMIN) dei 10 team LEC.
 */
@RestController
@RequestMapping("/api/teams")
@RequiredArgsConstructor
@Tag(name = "Team LEC", description = "Anagrafica delle organizzazioni LEC")
public class LecTeamController {

    private final LecTeamService lecTeamService;

    @GetMapping
    public List<LecTeamResponse> findAll() {
        return lecTeamService.findAll();
    }

    @GetMapping("/{id}")
    public LecTeamResponse findById(@PathVariable Long id) {
        return lecTeamService.findById(id);
    }

    @PostMapping
    public ResponseEntity<LecTeamResponse> create(@Valid @RequestBody LecTeamRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(lecTeamService.create(request));
    }

    @PutMapping("/{id}")
    public LecTeamResponse update(@PathVariable Long id, @Valid @RequestBody LecTeamRequest request) {
        return lecTeamService.update(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        lecTeamService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
