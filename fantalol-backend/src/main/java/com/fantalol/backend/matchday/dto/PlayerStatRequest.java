package com.fantalol.backend.matchday.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

public record PlayerStatRequest(
        @NotNull(message = "Il player è obbligatorio") Long lecPlayerId,
        @NotNull(message = "Il voto base è obbligatorio") Double votoBase,
        @Min(0) Integer kills,
        @Min(0) Integer morti,
        @Min(0) Integer assist,
        boolean mvp,
        boolean vittoria
) {
}
