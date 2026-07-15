package com.fantalol.backend.user;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.security.JwtUtil;
import com.fantalol.backend.user.dto.*;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Contiene la logica applicativa relativa a registrazione, login e gestione profilo utente.
 * Programmazione per interfacce: {@link UserRepository} e {@link PasswordEncoder} sono astrazioni
 * iniettate da Spring, non implementazioni concrete.
 */
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthenticationManager authenticationManager;
    private final JwtUtil jwtUtil;

    @Transactional
    public UserResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            throw new BusinessRuleException("Username già in uso: " + request.username());
        }
        if (userRepository.existsByEmail(request.email())) {
            throw new BusinessRuleException("Email già registrata: " + request.email());
        }

        User user = User.builder()
                .username(request.username())
                .email(request.email())
                .password(passwordEncoder.encode(request.password()))
                .role(Role.USER)
                .enabled(true)
                .build();

        User saved = userRepository.save(user);
        return UserResponse.from(saved);
    }

    public AuthResponse login(LoginRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.username(), request.password())
        );

        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new ResourceNotFoundException("Utente non trovato: " + request.username()));

        String token = jwtUtil.generateToken(user);
        return AuthResponse.of(token, user.getUsername(), user.getRole().name());
    }

    public UserResponse getByUsername(String username) {
        User user = findByUsernameOrThrow(username);
        return UserResponse.from(user);
    }

    @Transactional
    public UserResponse updateProfile(String username, UserProfileRequest request) {
        User user = findByUsernameOrThrow(username);

        UserProfile profile = user.getProfile();
        if (profile == null) {
            profile = UserProfile.builder().user(user).build();
            user.setProfile(profile);
        }
        profile.setNomeVisualizzato(request.nomeVisualizzato());
        profile.setBio(request.bio());
        profile.setAvatarUrl(request.avatarUrl());
        profile.setSummonerName(request.summonerName());

        User saved = userRepository.save(user);
        return UserResponse.from(saved);
    }

    public User findByUsernameOrThrow(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new ResourceNotFoundException("Utente non trovato: " + username));
    }
}
