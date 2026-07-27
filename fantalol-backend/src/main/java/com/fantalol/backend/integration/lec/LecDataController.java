package com.fantalol.backend.integration.lec;

import com.fantalol.backend.common.ResourceNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;

@RestController
@RequiredArgsConstructor
public class LecDataController {
    private final LecLiveDataService service;

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
    public LecDataSnapshot synchronize() {
        return service.synchronize();
    }

    private static <T> LecSection<T> section(LecDataSnapshot snapshot, List<T> items) {
        return new LecSection<>(
                snapshot.status(), snapshot.lastUpdatedAt(), snapshot.provisional(), items);
    }

    public record LecSection<T>(String status, Instant lastUpdatedAt, boolean provisional, List<T> items) {
    }
}
