package com.fantalol.backend.integration.lec;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.integration.oracle.PlayerGameCorrectionService;
import com.fantalol.backend.integration.oracle.dto.ManualPlayerGameCorrectionRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;

@RestController
@RequiredArgsConstructor
public class LecDataController {
    private final LecLiveDataService service;
    private final LecSynchronizationService synchronizationService;
    private final PlayerGameCorrectionService correctionService;

    @GetMapping("/api/lec/standings")
    public LecSection<LecDataSnapshot.Standing> standings() {
        LecDataSnapshot snapshot = service.current();
        return section(snapshot, snapshot.standings());
    }

    @GetMapping("/api/lec/performances")
    public LecSection<LecDataSnapshot.PlayerPerformance> performances() {
        LecDataSnapshot snapshot = service.current();
        return section(snapshot, snapshot.performances());
    }

    @GetMapping("/api/lec/matches")
    public LecSection<LecDataSnapshot.MatchSummary> matches() {
        LecDataSnapshot snapshot = service.current();
        return section(snapshot, snapshot.matches());
    }

    @GetMapping("/api/lec/matches/{matchId}/games/{gameId}")
    public LecDataSnapshot.GameSummary game(@PathVariable String matchId, @PathVariable String gameId) {
        return service.current().matches().stream()
                .filter(match -> match.id().equals(matchId))
                .flatMap(match -> match.games().stream())
                .filter(game -> game.id().equals(gameId))
                .findFirst()
                .orElseThrow(() -> new ResourceNotFoundException("LEC game not found: " + gameId));
    }

    @PostMapping("/api/admin/lec/synchronize")
    public SyncReport synchronize() {
        return synchronizationService.synchronize(SyncTrigger.MANUAL);
    }

    @GetMapping("/api/admin/lec/synchronization")
    public LecSyncStatusResponse synchronizationStatus() {
        return synchronizationService.status();
    }

    @PutMapping("/api/admin/lec/games/{gameId}/players/{playerId}")
    public void correctPlayerGame(
            @PathVariable String gameId,
            @PathVariable Long playerId,
            @Valid @RequestBody ManualPlayerGameCorrectionRequest request,
            Authentication authentication
    ) {
        correctionService.correct(gameId, playerId, request, authentication.getName());
    }

    @DeleteMapping("/api/admin/lec/games/{gameId}/players/{playerId}/override")
    public void restorePlayerGame(@PathVariable String gameId, @PathVariable Long playerId) {
        correctionService.restore(gameId, playerId);
    }

    private static <T> LecSection<T> section(LecDataSnapshot snapshot, List<T> items) {
        return new LecSection<>(
                snapshot.status(), snapshot.lastUpdatedAt(), snapshot.provisional(), items);
    }

    public record LecSection<T>(String status, Instant lastUpdatedAt, boolean provisional, List<T> items) {
    }
}
