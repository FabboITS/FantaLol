package com.fantalol.backend.config;

import com.fantalol.backend.league.League;
import com.fantalol.backend.league.LeagueRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class AdminAccountInitializerIntegrationTest {

    @Autowired
    private AdminAccountInitializer initializer;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private LeagueRepository leagueRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @BeforeEach
    void resetUsersAndLeagues() {
        leagueRepository.deleteAll();
        userRepository.deleteAll();
    }

    @Test
    void legacyAdminTriggersCompleteUserAndLeagueReset() {
        User legacyAdmin = userRepository.save(user("admin", "legacy-admin@fantalol.local", Role.ADMIN));
        User regularUser = userRepository.save(user("legacy-user", "legacy-user@fantalol.local", Role.USER));
        leagueRepository.save(League.builder()
                .nome("Legacy League")
                .creditiIniziali(1000)
                .admin(regularUser)
                .build());

        initializer.initialize();

        assertThat(leagueRepository.count()).isZero();
        assertThat(userRepository.findAll())
                .singleElement()
                .satisfies(admin -> {
                    assertThat(admin.getUsername()).isEqualTo("Natsu_Admin");
                    assertThat(admin.getRole()).isEqualTo(Role.ADMIN);
                    assertThat(admin.isEnabled()).isTrue();
                    assertThat(admin.getPassword()).startsWith("$2");
                    assertThat(admin.getPassword()).isNotEqualTo(legacyAdmin.getPassword());
                });
    }

    @Test
    void laterStartupsPreserveUsersCreatedAfterMigration() {
        userRepository.save(user("admin", "legacy-admin@fantalol.local", Role.ADMIN));
        initializer.initialize();
        userRepository.save(user("future-user", "future-user@fantalol.local", Role.USER));

        initializer.initialize();

        assertThat(userRepository.findAll())
                .extracting(User::getUsername)
                .containsExactlyInAnyOrder("Natsu_Admin", "future-user");
    }

    @Test
    void freshDatabaseCreatesNewAdministrator() {
        initializer.initialize();

        assertThat(userRepository.findAll())
                .singleElement()
                .satisfies(admin -> {
                    assertThat(admin.getUsername()).isEqualTo("Natsu_Admin");
                    assertThat(admin.getEmail()).isEqualTo("natsu-admin@fantalol.local");
                    assertThat(admin.getRole()).isEqualTo(Role.ADMIN);
                    assertThat(admin.getPassword()).startsWith("$2");
                });
    }

    private User user(String username, String email, Role role) {
        return User.builder()
                .username(username)
                .email(email)
                .password(passwordEncoder.encode("test-only-password"))
                .role(role)
                .enabled(true)
                .build();
    }
}
