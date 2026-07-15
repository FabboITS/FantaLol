package com.fantalol.backend.matchday.dto;

import jakarta.validation.constraints.NotNull;

import java.time.LocalDate;

public record MatchdayRequest(
        @NotNull(message = "La lega è obbligatoria") Long leagueId,
        @NotNull(message = "Il numero di giornata è obbligatorio") Integer numero,
        String descrizione,
        LocalDate data
) {
}
