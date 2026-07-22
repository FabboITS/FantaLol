package com.fantalol.backend.user.dto;

import com.fantalol.backend.user.User;

public record UserDirectoryEntry(String username, String email) {

    public static UserDirectoryEntry from(User user) {
        return new UserDirectoryEntry(user.getUsername(), user.getEmail());
    }
}
