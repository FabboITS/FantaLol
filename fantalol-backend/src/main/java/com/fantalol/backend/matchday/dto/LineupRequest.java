package com.fantalol.backend.matchday.dto;

import jakarta.validation.constraints.NotEmpty;

import java.util.List;

public record LineupRequest(
        @NotEmpty(message = "Devi schierare almeno un titolare") List<Long> titolariIds
) {
}
