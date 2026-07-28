package com.fantalol.backend.user;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.user.dto.LoginRequest;
import com.fantalol.backend.user.dto.RegisterRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Test di integrazione end-to-end: verifica il flusso completo di registrazione + login
 * e che gli endpoint protetti rispondano correttamente in base alla presenza/assenza del token JWT.
 * Utilizza un database H2 in memoria (profilo "test").
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AuthIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Test
    void registrazioneELoginRestituisconoUnTokenValido() throws Exception {
        RegisterRequest registerRequest = new RegisterRequest("integrazione", "integrazione@fantalol.it", "password123");

        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(registerRequest)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.username").value("integrazione"));

        LoginRequest loginRequest = new LoginRequest("integrazione", "password123");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(loginRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andExpect(jsonPath("$.role").value("USER"));
    }

    @Test
    void nonPermetteLaRegistrazioneConDatiNonValidi() throws Exception {
        RegisterRequest invalido = new RegisterRequest("ab", "non-una-email", "123");

        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalido)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void gliEndpointDiConsultazionePubblicaSonoAccessibiliSenzaToken() throws Exception {
        mockMvc.perform(get("/api/teams"))
                .andExpect(status().isOk());
    }

    @Test
    void gliEndpointProtettiRichiedonoUnTokenValido() throws Exception {
        mockMvc.perform(get("/api/users/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void unUtenteAutenticatoPuoAccedereAlProprioProfilo() throws Exception {
        RegisterRequest registerRequest = new RegisterRequest("profiluser", "profiluser@fantalol.it", "password123");
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(registerRequest)))
                .andExpect(status().isCreated());

        String loginResponse = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(new LoginRequest("profiluser", "password123"))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();

        String token = objectMapper.readTree(loginResponse).get("token").asText();

        mockMvc.perform(get("/api/users/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("profiluser"));
    }

    @Test
    void tokenDiUnUtenteEliminatoRestituisceUnauthorized() throws Exception {
        RegisterRequest request = new RegisterRequest(
                "deleted-token-user",
                "deleted-token-user@fantalol.it",
                "password123");
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated());

        String loginResponse = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(
                                new LoginRequest("deleted-token-user", "password123"))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        String token = objectMapper.readTree(loginResponse).get("token").asText();

        userRepository.delete(userRepository.findByUsername("deleted-token-user").orElseThrow());

        mockMvc.perform(get("/api/users/me")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void synchronizationAndCorrectionRoutesRequireGlobalAdmin() throws Exception {
        RegisterRequest request = new RegisterRequest("sync-user", "sync-user@fantalol.it", "password123");
        mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated());
        String userToken = token("sync-user", "password123");

        mockMvc.perform(get("/api/admin/lec/synchronization")
                        .header("Authorization", "Bearer " + userToken))
                .andExpect(status().isForbidden());
        mockMvc.perform(post("/api/admin/lec/synchronize")
                        .header("Authorization", "Bearer " + userToken))
                .andExpect(status().isForbidden());
        mockMvc.perform(put("/api/admin/lec/games/GAME-1/players/1")
                        .header("Authorization", "Bearer " + userToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isForbidden());
        mockMvc.perform(delete("/api/admin/lec/games/GAME-1/players/1/override")
                        .header("Authorization", "Bearer " + userToken))
                .andExpect(status().isForbidden());

        userRepository.save(User.builder()
                .username("sync-admin")
                .email("sync-admin@fantalol.it")
                .password(passwordEncoder.encode("password123"))
                .role(Role.ADMIN)
                .build());
        String adminToken = token("sync-admin", "password123");
        mockMvc.perform(get("/api/admin/lec/synchronization")
                        .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk());
    }

    private String token(String username, String password) throws Exception {
        String response = mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(new LoginRequest(username, password))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return objectMapper.readTree(response).get("token").asText();
    }
}
