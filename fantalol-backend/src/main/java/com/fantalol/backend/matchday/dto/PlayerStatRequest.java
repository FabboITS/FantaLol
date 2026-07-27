package com.fantalol.backend.matchday.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

public record PlayerStatRequest(
        @NotNull(message = "Il player è obbligatorio") Long lecPlayerId,
        @Min(0) Integer kills,
        @Min(0) Integer morti,
        @Min(0) Integer assist,
        @Min(0) Integer cs,
        @Min(0) Integer visionScore,
        boolean vittoria
) {
}
