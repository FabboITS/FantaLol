package com.fantalol.backend.team.dto;

import jakarta.validation.constraints.NotBlank;

public record LecTeamRequest(
        @NotBlank(message = "Il nome del team è obbligatorio") String nome,
        String sigla,
        String logoUrl
) {
}
