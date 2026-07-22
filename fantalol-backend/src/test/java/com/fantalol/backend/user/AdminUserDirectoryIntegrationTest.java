package com.fantalol.backend.user;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;

import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AdminUserDirectoryIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
        userRepository.save(user("zeta", Role.USER));
        userRepository.save(user("alpha", Role.USER));
        userRepository.save(user("admin-test", Role.ADMIN));
    }

    @Test
    @WithMockUser(username = "admin-test", roles = "ADMIN")
    void adminReceivesSortedRegularUsersWithUsernameAndEmailOnly() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].username").value("alpha"))
                .andExpect(jsonPath("$[0].email").value("alpha@test.local"))
                .andExpect(jsonPath("$[1].username").value("zeta"))
                .andExpect(jsonPath("$[1].email").value("zeta@test.local"))
                .andExpect(jsonPath("$[0].id").doesNotExist())
                .andExpect(jsonPath("$[0].password").doesNotExist())
                .andExpect(jsonPath("$[0].role").doesNotExist())
                .andExpect(jsonPath("$[0].profile").doesNotExist());
    }

    @Test
    @WithMockUser(username = "alpha", roles = "USER")
    void regularUserCannotReadDirectory() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isForbidden());
    }

    @Test
    void anonymousUserCannotReadDirectory() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "admin-test", roles = "ADMIN")
    void adminAccountsAreExcludedFromDirectory() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].username", not(hasItem("admin-test"))));
    }

    private User user(String username, Role role) {
        return User.builder()
                .username(username)
                .email(username + "@test.local")
                .password("encoded-not-returned")
                .role(role)
                .enabled(true)
                .createdAt(Instant.now())
                .build();
    }
}
