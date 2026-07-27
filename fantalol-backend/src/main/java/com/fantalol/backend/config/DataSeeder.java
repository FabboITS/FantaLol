package com.fantalol.backend.config;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.LecTeam;
import com.fantalol.backend.team.LecTeamRepository;
import com.fantalol.backend.team.PlayerRole;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Popola il database, all'avvio dell'applicazione, con:
 * <ul>
 *     <li>i 10 team della LEC e i relativi roster reali (Spring Split 2026)</li>
 *     <li>un utente amministratore di default</li>
 * </ul>
 * I dati LEC vengono inseriti solo se assenti; l'inizializzazione amministrativa
 * viene invece verificata a ogni avvio ed esegue la migrazione legacy una sola volta.
 */
@Component
@RequiredArgsConstructor
public class DataSeeder implements CommandLineRunner {

    private final LecTeamRepository lecTeamRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final AdminAccountInitializer adminAccountInitializer;

    private record PlayerSeed(String nickname, PlayerRole ruolo, String nazionalita, int quotazione) {
    }

    private record RosterCorrection(
            String currentNickname,
            String correctedNickname,
            String nationality,
            String teamName
    ) {
    }

    private static final List<RosterCorrection> ROSTER_CORRECTIONS = List.of(
            new RosterCorrection("Empyros", "Soboro", "Corea del Sud", "Fnatic"),
            new RosterCorrection("Lot", "Oscarinin", "Spagna", "GIANTX"),
            new RosterCorrection("Sheo", "Sheo", null, "Shifters"),
            new RosterCorrection("Boukada", "Daglas", "Polonia", "Team Heretics"),
            new RosterCorrection("Humanoid", "FIESTA", "Corea del Sud", "Team Vitality"),
            new RosterCorrection("LIDER", "SlowQ", "Corea del Sud", "SK Gaming"),
            new RosterCorrection("Noah", "Flakked", "Spagna", "GIANTX"),
            new RosterCorrection("Ice", "Hype", "Corea del Sud", "Team Heretics"),
            new RosterCorrection("Stend", "Stend", null, "Shifters"),
            new RosterCorrection("Trymbi", "Way", "Corea del Sud", "Team Heretics")
    );

    @Override
    public void run(String... args) {
        if (lecTeamRepository.count() > 0) {
            synchronizeExistingRoster();
            backfillExistingAssetMetadata();
        } else {
            seedLecTeams();
        }

        adminAccountInitializer.initialize();
    }

    private void seedLecTeams() {

        seedTeam("Team Vitality", "VIT", List.of(
                new PlayerSeed("Naak Nako", PlayerRole.TOP, "Turchia", 55),
                new PlayerSeed("Lyncas", PlayerRole.JUNGLE, "Lituania", 50),
                new PlayerSeed("FIESTA", PlayerRole.MID, "Corea del Sud", 75),
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
                new PlayerSeed("SamD", PlayerRole.ADC, "Corea del Sud", 55),
                new PlayerSeed("Parus", PlayerRole.SUPPORT, "Turchia", 50)
        ));

        seedTeam("GIANTX", "GX", List.of(
                new PlayerSeed("Oscarinin", PlayerRole.TOP, "Spagna", 55),
                new PlayerSeed("Isma", PlayerRole.JUNGLE, "Francia", 55),
                new PlayerSeed("Jackies", PlayerRole.MID, "Repubblica Ceca", 60),
                new PlayerSeed("Flakked", PlayerRole.ADC, "Spagna", 60),
                new PlayerSeed("Jun", PlayerRole.SUPPORT, "Corea del Sud", 55)
        ));

        seedTeam("Fnatic", "FNC", List.of(
                new PlayerSeed("Soboro", PlayerRole.TOP, "Corea del Sud", 55),
                new PlayerSeed("Razork", PlayerRole.JUNGLE, "Spagna", 75),
                new PlayerSeed("Vladi", PlayerRole.MID, "Grecia", 70),
                new PlayerSeed("Upset", PlayerRole.ADC, "Germania", 80),
                new PlayerSeed("Lospa", PlayerRole.SUPPORT, "Corea del Sud", 60)
        ));

        seedTeam("SK Gaming", "SK", List.of(
                new PlayerSeed("Wunder", PlayerRole.TOP, "Danimarca", 65),
                new PlayerSeed("Skeanz", PlayerRole.JUNGLE, "Francia", 55),
                new PlayerSeed("SlowQ", PlayerRole.MID, "Corea del Sud", 55),
                new PlayerSeed("Jopa", PlayerRole.ADC, "Croazia", 50),
                new PlayerSeed("Mikyx", PlayerRole.SUPPORT, "Slovenia", 75)
        ));

        seedTeam("Shifters", "SHFT", List.of(
                new PlayerSeed("Rooster", PlayerRole.TOP, "Corea del Sud", 55),
                new PlayerSeed("Sheo", PlayerRole.JUNGLE, "Francia", 60),
                new PlayerSeed("nuc", PlayerRole.MID, "Marocco/Francia", 55),
                new PlayerSeed("Paduck", PlayerRole.ADC, "Corea del Sud", 55),
                new PlayerSeed("Stend", PlayerRole.SUPPORT, "Francia", 55)
        ));

        seedTeam("Team Heretics", "TH", List.of(
                new PlayerSeed("Tracyn", PlayerRole.TOP, "Polonia", 50),
                new PlayerSeed("Daglas", PlayerRole.JUNGLE, "Polonia", 55),
                new PlayerSeed("Serin", PlayerRole.MID, "Turchia", 55),
                new PlayerSeed("Hype", PlayerRole.ADC, "Corea del Sud", 55),
                new PlayerSeed("Way", PlayerRole.SUPPORT, "Corea del Sud", 60)
        ));

    }

    private void synchronizeExistingRoster() {
        for (RosterCorrection correction : ROSTER_CORRECTIONS) {
            var targetTeam = lecTeamRepository.findByNomeIgnoreCase(correction.teamName());
            if (targetTeam.isEmpty()) {
                continue;
            }
            var player = lecPlayerRepository.findFirstByNicknameIgnoreCase(correction.currentNickname())
                    .or(() -> lecPlayerRepository.findFirstByNicknameIgnoreCase(correction.correctedNickname()));
            if (player.isEmpty()) {
                continue;
            }
            LecPlayer existingPlayer = player.orElseThrow();
            existingPlayer.setNickname(correction.correctedNickname());
            if (correction.nationality() != null) {
                existingPlayer.setNazionalita(correction.nationality());
            }
            existingPlayer.setTeam(targetTeam.orElseThrow());
            lecPlayerRepository.save(existingPlayer);
        }
    }

    private void backfillExistingAssetMetadata() {
        for (LecTeam team : lecTeamRepository.findAll()) {
            team.setLogoUrl(teamLogoUrl(team.getNome()));
            lecTeamRepository.save(team);
        }
        for (LecPlayer player : lecPlayerRepository.findAll()) {
            if ("Hans SamD".equals(player.getNickname())) {
                player.setNickname("SamD");
            }
            player.setImageUrl(playerImageUrl(player.getNickname(), player.getRuolo()));
            lecPlayerRepository.save(player);
        }
    }

    private void seedTeam(String nome, String sigla, List<PlayerSeed> giocatori) {
        LecTeam team = lecTeamRepository.save(LecTeam.builder()
                .nome(nome)
                .sigla(sigla)
                .logoUrl(teamLogoUrl(nome))
                .build());

        for (PlayerSeed seed : giocatori) {
            lecPlayerRepository.save(LecPlayer.builder()
                    .nickname(seed.nickname())
                    .ruolo(seed.ruolo())
                    .nazionalita(seed.nazionalita())
                    .imageUrl(playerImageUrl(seed))
                    .quotazione(seed.quotazione())
                    .team(team)
                    .build());
        }
    }

    private String playerImageUrl(PlayerSeed player) {
        return playerImageUrl(player.nickname(), player.ruolo());
    }

    private String playerImageUrl(String nickname, PlayerRole playerRole) {
        String role = switch (playerRole) {
            case TOP -> "Top";
            case JUNGLE -> "Jungle";
            case MID -> "Mid";
            case ADC -> "Adc";
            case SUPPORT -> "Support";
        };
        String filename = switch (nickname) {
            case "Naak Nako" -> "Naak_Nako";
            case "Hans Sama" -> "Hans_Sama";
            case "Isma" -> "ISMA";
            default -> nickname;
        };
        return "/Player_immage/" + role + "/" + filename + ".jpg";
    }

    private String teamLogoUrl(String teamName) {
        return switch (teamName) {
            case "Team Vitality" -> "/assets/team-logos/team-vitality.ico";
            case "Karmine Corp" -> "/assets/team-logos/karmine-corp.png";
            case "G2 Esports" -> "/assets/team-logos/g2-esports.png";
            case "Movistar KOI" -> "/assets/team-logos/movistar-koi.png";
            case "Natus Vincere" -> "/assets/team-logos/natus-vincere.ico";
            case "GIANTX" -> "/assets/team-logos/giantx.svg";
            case "Fnatic" -> "/assets/team-logos/fnatic.png";
            case "SK Gaming" -> "/assets/team-logos/sk-gaming.ico";
            case "Shifters" -> "/assets/team-logos/shifters.ico";
            case "Team Heretics" -> "/assets/team-logos/team-heretics.png";
            default -> null;
        };
    }

}
