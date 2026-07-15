package com.fantalol.backend.team.dto;

import com.fantalol.backend.team.PlayerRole;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record LecPlayerRequest(
        @NotBlank(message = "Il nickname è obbligatorio") String nickname,
        String nomeReale,
        String nazionalita,
        @NotNull(message = "Il ruolo è obbligatorio") PlayerRole ruolo,
        @NotNull(message = "La quotazione è obbligatoria") @Positive Integer quotazione,
        @NotNull(message = "Il team è obbligatorio") Long teamId,
        String imageUrl
) {
}
