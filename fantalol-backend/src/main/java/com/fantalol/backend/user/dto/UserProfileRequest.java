package com.fantalol.backend.user.dto;

import jakarta.validation.constraints.Size;

public record UserProfileRequest(
        @Size(max = 60) String nomeVisualizzato,
        @Size(max = 255) String bio,
        @Size(max = 255) String avatarUrl,
        @Size(max = 60) String summonerName
) {
}
