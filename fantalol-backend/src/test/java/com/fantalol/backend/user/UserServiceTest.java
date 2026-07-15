package com.fantalol.backend.user;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.security.JwtUtil;
import com.fantalol.backend.user.dto.LoginRequest;
import com.fantalol.backend.user.dto.RegisterRequest;
import com.fantalol.backend.user.dto.UserResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;
    @Mock
    private PasswordEncoder passwordEncoder;
    @Mock
    private AuthenticationManager authenticationManager;
    @Mock
    private JwtUtil jwtUtil;

    @InjectMocks
    private UserService userService;

    private RegisterRequest registerRequest;

    @BeforeEach
    void setUp() {
        registerRequest = new RegisterRequest("mago", "mago@fantalol.it", "password123");
    }

    @Test
    void registraCorrettamenteUnNuovoUtente() {
        when(userRepository.existsByUsername("mago")).thenReturn(false);
        when(userRepository.existsByEmail("mago@fantalol.it")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("hash");
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> {
            User u = invocation.getArgument(0);
            u.setId(1L);
            return u;
        });

        UserResponse response = userService.register(registerRequest);

        assertThat(response.username()).isEqualTo("mago");
        assertThat(response.email()).isEqualTo("mago@fantalol.it");
        assertThat(response.role()).isEqualTo("USER");
        verify(userRepository).save(any(User.class));
    }

    @Test
    void lanciaEccezioneSeUsernameGiaEsistente() {
        when(userRepository.existsByUsername("mago")).thenReturn(true);

        assertThatThrownBy(() -> userService.register(registerRequest))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("Username già in uso");

        verify(userRepository, never()).save(any());
    }

    @Test
    void lanciaEccezioneSeEmailGiaRegistrata() {
        when(userRepository.existsByUsername("mago")).thenReturn(false);
        when(userRepository.existsByEmail("mago@fantalol.it")).thenReturn(true);

        assertThatThrownBy(() -> userService.register(registerRequest))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("Email già registrata");
    }

    @Test
    void effettuaIlLoginERestituisceUnToken() {
        User user = User.builder().id(1L).username("mago").email("mago@fantalol.it")
                .password("hash").role(Role.USER).enabled(true).build();

        when(userRepository.findByUsername("mago")).thenReturn(Optional.of(user));
        when(jwtUtil.generateToken(user)).thenReturn("fake-jwt-token");

        var response = userService.login(new LoginRequest("mago", "password123"));

        assertThat(response.token()).isEqualTo("fake-jwt-token");
        assertThat(response.username()).isEqualTo("mago");
        verify(authenticationManager).authenticate(any());
    }
}
