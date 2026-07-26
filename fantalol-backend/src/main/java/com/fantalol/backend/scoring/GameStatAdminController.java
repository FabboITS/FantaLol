package com.fantalol.backend.scoring;

import com.fantalol.backend.scoring.dto.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/game-stats")
@RequiredArgsConstructor
public class GameStatAdminController {
    private final GameStatService service;

    @PutMapping
    public GameStatResponse insertManual(Authentication authentication,
                                         @Valid @RequestBody ManualGameStatRequest request) {
        return service.insertManual(authentication.getName(), request);
    }

    @GetMapping("/conflicts")
    public List<StatConflictResponse> conflicts() {
        return service.conflicts();
    }

    @PostMapping("/conflicts/{id}/resolve")
    public GameStatResponse resolve(Authentication authentication, @PathVariable Long id,
                                    @Valid @RequestBody ResolveConflictRequest request) {
        return service.resolve(id, request.source(), authentication.getName());
    }
}
