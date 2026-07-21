package com.fantalol.backend.matchday.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public record FormationRequest(
        @NotNull(message = "La giornata è obbligatoria") Long matchdayId,
        @NotEmpty(message = "Devi schierare almeno un titolare") List<Long> titolariIds
) {
}
