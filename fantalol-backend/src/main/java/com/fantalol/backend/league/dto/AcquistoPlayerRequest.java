package com.fantalol.backend.league.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record AcquistoPlayerRequest(
        @NotNull(message = "Il player è obbligatorio") Long lecPlayerId,
        @NotNull(message = "I crediti offerti sono obbligatori") @Positive Integer creditiOfferti
) {
}
