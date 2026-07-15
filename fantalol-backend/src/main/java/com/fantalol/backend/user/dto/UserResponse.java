package com.fantalol.backend.user.dto;

import com.fantalol.backend.user.User;

public record UserResponse(
        Long id,
        String username,
        String email,
        String role,
        String nomeVisualizzato
) {
    public static UserResponse from(User user) {
        String nomeVisualizzato = user.getProfile() != null ? user.getProfile().getNomeVisualizzato() : null;
        return new UserResponse(user.getId(), user.getUsername(), user.getEmail(), user.getRole().name(), nomeVisualizzato);
    }
}
