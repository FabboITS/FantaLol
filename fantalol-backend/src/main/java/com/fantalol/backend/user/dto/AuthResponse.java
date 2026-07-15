package com.fantalol.backend.user.dto;

public record AuthResponse(
        String token,
        String tokenType,
        String username,
        String role
) {
    public static AuthResponse of(String token, String username, String role) {
        return new AuthResponse(token, "Bearer", username, role);
    }
}
