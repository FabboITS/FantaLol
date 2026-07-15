package com.fantalol.backend.league.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

public record LeagueRequest(
        @NotBlank(message = "Il nome della lega è obbligatorio") String nome,
        @Positive(message = "I crediti iniziali devono essere positivi") Integer creditiIniziali
) {
}
