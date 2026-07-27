package com.fantalol.backend.common;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.HashSet;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

class SeedAssetReferenceTest {

    private static final Pattern PLAYER_IMAGE = Pattern.compile("'(/Player_immage/[^']+\\.jpg)'");
    private static final Pattern TEAM_LOGO = Pattern.compile("'(/assets/team-logos/[^']+\\.(?:svg|png|webp|ico))'");
    private static final List<String> REPLACEMENT_PORTRAITS = List.of(
            "/Player_immage/Top/Soboro.jpg",
            "/Player_immage/Top/Oscarinin.jpg",
            "/Player_immage/Jungle/Daglas.jpg",
            "/Player_immage/Mid/FIESTA.jpg",
            "/Player_immage/Mid/SlowQ.jpg",
            "/Player_immage/Adc/Flakked.jpg",
            "/Player_immage/Adc/Hype.jpg",
            "/Player_immage/Support/Way.jpg"
    );

    @Test
    void everySeededPlayerReferencesAnExistingPortrait() throws IOException {
        var paths = matches(PLAYER_IMAGE);
        assertThat(paths).hasSize(50);
        assertThat(paths).containsAll(REPLACEMENT_PORTRAITS);
        assertThat(paths).allSatisfy(this::assertFrontendAssetExists);
    }

    @Test
    void sqlSeedUsesTheCorrectedTeamAssignments() throws IOException {
        String seed = Files.readString(Path.of("sql/data-seed.sql"));

        assertThat(seed)
                .contains(playerRow("Sheo", "Francia", "JUNGLE", 60, "Shifters"))
                .contains(playerRow("Stend", "Francia", "SUPPORT", 55, "Shifters"))
                .contains(playerRow("Daglas", "Polonia", "JUNGLE", 55, "Team Heretics"))
                .contains(playerRow("Way", "Corea del Sud", "SUPPORT", 60, "Team Heretics"));
    }

    @Test
    void everySeededTeamReferencesAnExistingLogo() throws IOException {
        var paths = matches(TEAM_LOGO);
        assertThat(paths).hasSize(10);
        assertThat(paths).allSatisfy(this::assertFrontendAssetExists);
    }

    private HashSet<String> matches(Pattern pattern) throws IOException {
        String seed = Files.readString(Path.of("sql/data-seed.sql"));
        var matches = new HashSet<String>();
        pattern.matcher(seed).results().forEach(result -> matches.add(result.group(1)));
        return matches;
    }

    private void assertFrontendAssetExists(String webPath) {
        Path asset = Path.of("..", "fantalol-frontend", webPath.substring(1)).normalize();
        assertThat(asset).as(webPath).isRegularFile();
    }

    private String playerRow(String nickname, String nationality, String role, int quotation, String teamName) {
        return "('" + nickname + "', NULL, '" + nationality + "', '" + role + "', " + quotation
                + ", (SELECT id FROM lec_teams WHERE nome = '" + teamName + "'))";
    }
}
