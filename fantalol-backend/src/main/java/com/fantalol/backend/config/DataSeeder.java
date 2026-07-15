package com.fantalol.backend.config;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.LecTeam;
import com.fantalol.backend.team.LecTeamRepository;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Popola il database, all'avvio dell'applicazione, con:
 * <ul>
 *     <li>i 10 team della LEC e i relativi roster reali (Spring Split 2026)</li>
 *     <li>un utente amministratore di default</li>
 * </ul>
 * L'inserimento avviene solo se il database è vuoto, per non duplicare i dati ad ogni riavvio.
 */
@Component
@RequiredArgsConstructor
public class DataSeeder implements CommandLineRunner {

    private final LecTeamRepository lecTeamRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    private record PlayerSeed(String nickname, PlayerRole ruolo, String nazionalita, int quotazione) {
    }

    @Override
    public void run(String... args) {
        if (lecTeamRepository.count() > 0) {
            return; // dati già presenti
        }

        seedTeam("Team Vitality", "VIT", List.of(
                new PlayerSeed("Naak Nako", PlayerRole.TOP, "Turchia", 55),
                new PlayerSeed("Lyncas", PlayerRole.JUNGLE, "Lituania", 50),
                new PlayerSeed("Humanoid", PlayerRole.MID, "Repubblica Ceca", 75),
                new PlayerSeed("Carzzy", PlayerRole.ADC, "Danimarca", 80),
                new PlayerSeed("Fleshy", PlayerRole.SUPPORT, "Turchia", 55)
        ));

        seedTeam("Karmine Corp", "KC", List.of(
                new PlayerSeed("Canna", PlayerRole.TOP, "Corea del Sud", 90),
                new PlayerSeed("Yike", PlayerRole.JUNGLE, "Danimarca", 80),
                new PlayerSeed("Kyeahoo", PlayerRole.MID, "Corea del Sud", 65),
                new PlayerSeed("Caliste", PlayerRole.ADC, "Francia", 85),
                new PlayerSeed("Busio", PlayerRole.SUPPORT, "Stati Uniti", 80)
        ));

        seedTeam("G2 Esports", "G2", List.of(
                new PlayerSeed("BrokenBlade", PlayerRole.TOP, "Germania/Turchia", 85),
                new PlayerSeed("SkewMond", PlayerRole.JUNGLE, "Francia/Libano", 80),
                new PlayerSeed("Caps", PlayerRole.MID, "Danimarca", 100),
                new PlayerSeed("Hans Sama", PlayerRole.ADC, "Francia", 90),
                new PlayerSeed("Labrov", PlayerRole.SUPPORT, "Grecia", 80)
        ));

        seedTeam("Movistar KOI", "MKOI", List.of(
                new PlayerSeed("Myrwn", PlayerRole.TOP, "Spagna", 65),
                new PlayerSeed("Elyoya", PlayerRole.JUNGLE, "Spagna", 95),
                new PlayerSeed("Jojopyun", PlayerRole.MID, "Stati Uniti", 85),
                new PlayerSeed("Supa", PlayerRole.ADC, "Spagna", 70),
                new PlayerSeed("Alvaro", PlayerRole.SUPPORT, "Spagna", 75)
        ));

        seedTeam("Natus Vincere", "NAVI", List.of(
                new PlayerSeed("Maynter", PlayerRole.TOP, "Ucraina", 55),
                new PlayerSeed("Rhilech", PlayerRole.JUNGLE, "Turchia", 60),
                new PlayerSeed("Poby", PlayerRole.MID, "Corea del Sud", 55),
                new PlayerSeed("Hans SamD", PlayerRole.ADC, "Corea del Sud", 55),
                new PlayerSeed("Parus", PlayerRole.SUPPORT, "Turchia", 50)
        ));

        seedTeam("GIANTX", "GX", List.of(
                new PlayerSeed("Lot", PlayerRole.TOP, "Turchia", 55),
                new PlayerSeed("Isma", PlayerRole.JUNGLE, "Francia", 55),
                new PlayerSeed("Jackies", PlayerRole.MID, "Repubblica Ceca", 60),
                new PlayerSeed("Noah", PlayerRole.ADC, "Corea del Sud", 60),
                new PlayerSeed("Jun", PlayerRole.SUPPORT, "Corea del Sud", 55)
        ));

        seedTeam("Fnatic", "FNC", List.of(
                new PlayerSeed("Empyros", PlayerRole.TOP, "Grecia", 55),
                new PlayerSeed("Razork", PlayerRole.JUNGLE, "Spagna", 75),
                new PlayerSeed("Vladi", PlayerRole.MID, "Grecia", 70),
                new PlayerSeed("Upset", PlayerRole.ADC, "Germania", 80),
                new PlayerSeed("Lospa", PlayerRole.SUPPORT, "Corea del Sud", 60)
        ));

        seedTeam("SK Gaming", "SK", List.of(
                new PlayerSeed("Wunder", PlayerRole.TOP, "Danimarca", 65),
                new PlayerSeed("Skeanz", PlayerRole.JUNGLE, "Francia", 55),
                new PlayerSeed("LIDER", PlayerRole.MID, "Norvegia", 55),
                new PlayerSeed("Jopa", PlayerRole.ADC, "Croazia", 50),
                new PlayerSeed("Mikyx", PlayerRole.SUPPORT, "Slovenia", 75)
        ));

        seedTeam("Shifters", "SHFT", List.of(
                new PlayerSeed("Rooster", PlayerRole.TOP, "Corea del Sud", 55),
                new PlayerSeed("Boukada", PlayerRole.JUNGLE, "Francia", 55),
                new PlayerSeed("nuc", PlayerRole.MID, "Marocco/Francia", 55),
                new PlayerSeed("Paduck", PlayerRole.ADC, "Corea del Sud", 55),
                new PlayerSeed("Trymbi", PlayerRole.SUPPORT, "Polonia", 60)
        ));

        seedTeam("Team Heretics", "TH", List.of(
                new PlayerSeed("Tracyn", PlayerRole.TOP, "Polonia", 50),
                new PlayerSeed("Sheo", PlayerRole.JUNGLE, "Francia", 60),
                new PlayerSeed("Serin", PlayerRole.MID, "Turchia", 55),
                new PlayerSeed("Ice", PlayerRole.ADC, "Corea del Sud", 55),
                new PlayerSeed("Stend", PlayerRole.SUPPORT, "Francia", 55)
        ));

        seedAdminUser();
    }

    private void seedTeam(String nome, String sigla, List<PlayerSeed> giocatori) {
        LecTeam team = lecTeamRepository.save(LecTeam.builder()
                .nome(nome)
                .sigla(sigla)
                .build());

        for (PlayerSeed seed : giocatori) {
            lecPlayerRepository.save(LecPlayer.builder()
                    .nickname(seed.nickname())
                    .ruolo(seed.ruolo())
                    .nazionalita(seed.nazionalita())
                    .quotazione(seed.quotazione())
                    .team(team)
                    .build());
        }
    }

    private void seedAdminUser() {
        if (userRepository.existsByUsername("admin")) {
            return;
        }
        User admin = User.builder()
                .username("admin")
                .email("admin@fantalol.local")
                .password(passwordEncoder.encode("Admin123!"))
                .role(Role.ADMIN)
                .enabled(true)
                .build();
        userRepository.save(admin);
    }
}
