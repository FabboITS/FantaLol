package com.fantalol.backend.matchday.dto;

import java.time.Instant;
import java.util.List;

public record LineupResponse(
        List<FormationPlayerResponse> players,
        List<FormationPlayerResponse> effectivePlayers,
        boolean editable,
        Instant nextEffectiveAt
) {
}
