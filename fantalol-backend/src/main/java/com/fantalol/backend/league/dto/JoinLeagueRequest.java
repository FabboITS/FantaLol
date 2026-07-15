package com.fantalol.backend.league.dto;

import jakarta.validation.constraints.NotBlank;

public record JoinLeagueRequest(
        @NotBlank(message = "Il codice invito è obbligatorio") String codiceInvito,
        @NotBlank(message = "Il nome della squadra è obbligatorio") String nomeSquadra
) {
}
