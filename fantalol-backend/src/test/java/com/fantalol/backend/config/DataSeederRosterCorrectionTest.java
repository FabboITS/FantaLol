package com.fantalol.backend.config;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.LecTeam;
import com.fantalol.backend.team.LecTeamRepository;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DataSeederRosterCorrectionTest {

    @Test
    void correctsExistingSummerRosterWithoutChangingQuotations() {
        LecTeam vitality = team("Team Vitality");
        LecTeam giantx = team("GIANTX");
        LecTeam fnatic = team("Fnatic");
        LecTeam skGaming = team("SK Gaming");
        LecTeam shifters = team("Shifters");
        LecTeam heretics = team("Team Heretics");
        List<LecTeam> teams = List.of(vitality, giantx, fnatic, skGaming, shifters, heretics);

        List<LecPlayer> players = new ArrayList<>(List.of(
                player("Empyros", PlayerRole.TOP, "Grecia", 55, fnatic),
                player("Lot", PlayerRole.TOP, "Turchia", 55, giantx),
                player("Sheo", PlayerRole.JUNGLE, "Francia", 60, heretics),
                player("Boukada", PlayerRole.JUNGLE, "Francia", 55, shifters),
                player("Humanoid", PlayerRole.MID, "Repubblica Ceca", 75, vitality),
                player("LIDER", PlayerRole.MID, "Norvegia", 55, skGaming),
                player("Noah", PlayerRole.ADC, "Corea del Sud", 60, giantx),
                player("Ice", PlayerRole.ADC, "Corea del Sud", 55, heretics),
                player("Stend", PlayerRole.SUPPORT, "Francia", 55, heretics),
                player("Trymbi", PlayerRole.SUPPORT, "Polonia", 60, shifters)
        ));

        DataSeeder seeder = seederForExistingRoster(teams, players);
        seeder.run();

        assertPlayer(players, "Soboro", PlayerRole.TOP, "Corea del Sud", 55, "Fnatic");
        assertPlayer(players, "Oscarinin", PlayerRole.TOP, "Spagna", 55, "GIANTX");
        assertPlayer(players, "Sheo", PlayerRole.JUNGLE, "Francia", 60, "Shifters");
        assertPlayer(players, "Daglas", PlayerRole.JUNGLE, "Polonia", 55, "Team Heretics");
        assertPlayer(players, "FIESTA", PlayerRole.MID, "Corea del Sud", 75, "Team Vitality");
        assertPlayer(players, "SlowQ", PlayerRole.MID, "Corea del Sud", 55, "SK Gaming");
        assertPlayer(players, "Flakked", PlayerRole.ADC, "Spagna", 60, "GIANTX");
        assertPlayer(players, "Hype", PlayerRole.ADC, "Corea del Sud", 55, "Team Heretics");
        assertPlayer(players, "Stend", PlayerRole.SUPPORT, "Francia", 55, "Shifters");
        assertPlayer(players, "Way", PlayerRole.SUPPORT, "Corea del Sud", 60, "Team Heretics");
    }

    @Test
    void appliesRosterCorrectionsIdempotently() {
        LecTeam shifters = team("Shifters");
        LecTeam heretics = team("Team Heretics");
        List<LecTeam> teams = List.of(shifters, heretics);
        List<LecPlayer> players = new ArrayList<>(List.of(
                player("Boukada", PlayerRole.JUNGLE, "Francia", 55, shifters),
                player("Trymbi", PlayerRole.SUPPORT, "Polonia", 60, shifters)
        ));

        DataSeeder seeder = seederForExistingRoster(teams, players);
        seeder.run();
        seeder.run();

        assertThat(players).extracting(LecPlayer::getNickname)
                .containsExactlyInAnyOrder("Daglas", "Way");
        assertPlayer(players, "Daglas", PlayerRole.JUNGLE, "Polonia", 55, "Team Heretics");
        assertPlayer(players, "Way", PlayerRole.SUPPORT, "Corea del Sud", 60, "Team Heretics");
    }

    private static DataSeeder seederForExistingRoster(List<LecTeam> teams, List<LecPlayer> players) {
        LecTeamRepository teamRepository = mock(LecTeamRepository.class);
        LecPlayerRepository playerRepository = mock(LecPlayerRepository.class);
        AdminAccountInitializer adminInitializer = mock(AdminAccountInitializer.class);

        when(teamRepository.count()).thenReturn((long) teams.size());
        when(teamRepository.findAll()).thenReturn(teams);
        when(teamRepository.findByNomeIgnoreCase(anyString())).thenAnswer(invocation ->
                teams.stream()
                        .filter(team -> team.getNome().equalsIgnoreCase(invocation.getArgument(0)))
                        .findFirst());
        when(playerRepository.findAll()).thenReturn(players);
        when(playerRepository.findFirstByNicknameIgnoreCase(anyString())).thenAnswer(invocation ->
                players.stream()
                        .filter(player -> player.getNickname().equalsIgnoreCase(invocation.getArgument(0)))
                        .findFirst());

        return new DataSeeder(teamRepository, playerRepository, adminInitializer);
    }

    private static LecTeam team(String name) {
        return LecTeam.builder().nome(name).build();
    }

    private static LecPlayer player(
            String nickname,
            PlayerRole role,
            String nationality,
            int quotation,
            LecTeam team
    ) {
        return LecPlayer.builder()
                .nickname(nickname)
                .ruolo(role)
                .nazionalita(nationality)
                .quotazione(quotation)
                .team(team)
                .build();
    }

    private static void assertPlayer(
            List<LecPlayer> players,
            String nickname,
            PlayerRole role,
            String nationality,
            int quotation,
            String teamName
    ) {
        Optional<LecPlayer> matchingPlayer = players.stream()
                .filter(player -> player.getNickname().equals(nickname))
                .findFirst();
        assertThat(matchingPlayer).as(nickname).isPresent();
        assertThat(matchingPlayer.orElseThrow().getRuolo()).isEqualTo(role);
        assertThat(matchingPlayer.orElseThrow().getNazionalita()).isEqualTo(nationality);
        assertThat(matchingPlayer.orElseThrow().getQuotazione()).isEqualTo(quotation);
        assertThat(matchingPlayer.orElseThrow().getTeam().getNome()).isEqualTo(teamName);
        assertThat(matchingPlayer.orElseThrow().getImageUrl())
                .isEqualTo("/Player_immage/" + imageRole(role) + "/" + nickname + ".jpg");
    }

    private static String imageRole(PlayerRole role) {
        return switch (role) {
            case TOP -> "Top";
            case JUNGLE -> "Jungle";
            case MID -> "Mid";
            case ADC -> "Adc";
            case SUPPORT -> "Support";
        };
    }
}
