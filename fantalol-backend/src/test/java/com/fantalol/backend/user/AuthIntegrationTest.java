package com.fantalol.backend.user;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fantalol.backend.user.dto.LoginRequest;
import com.fantalol.backend.user.dto.RegisterRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
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
}
