package com.fantalol.backend.user;

import com.fantalol.backend.user.dto.UserProfileRequest;
import com.fantalol.backend.user.dto.UserResponse;
import com.fantalol.backend.user.dto.UserDirectoryEntry;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Endpoint per la gestione del profilo dell'utente autenticato ("/me").
 * Richiede un token JWT valido (vedi {@code SecurityConfig}).
 */
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
@Tag(name = "Utenti", description = "Gestione del profilo utente autenticato")
public class UserController {

    private final UserService userService;

    @GetMapping
    public List<UserDirectoryEntry> getRegularUserDirectory() {
        return userService.getRegularUserDirectory();
    }

    @GetMapping("/me")
    public UserResponse getCurrentUser(Authentication authentication) {
        return userService.getByUsername(authentication.getName());
    }

    @PutMapping("/me/profile")
    public UserResponse updateProfile(Authentication authentication,
                                       @Valid @RequestBody UserProfileRequest request) {
        return userService.updateProfile(authentication.getName(), request);
    }
}
