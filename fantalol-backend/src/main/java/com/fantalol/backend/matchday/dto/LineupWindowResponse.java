package com.fantalol.backend.matchday.dto;

import java.time.Instant;

public record LineupWindowResponse(
        boolean editable,
        Instant nextEffectiveAt,
        String reason
) {
}
