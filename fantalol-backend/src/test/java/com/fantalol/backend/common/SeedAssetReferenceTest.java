package com.fantalol.backend.common;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

class SeedAssetReferenceTest {

    private static final Pattern PLAYER_IMAGE = Pattern.compile("'(/Player_immage/[^']+\\.jpg)'");
    private static final Pattern TEAM_LOGO = Pattern.compile("'(/assets/team-logos/[^']+\\.(?:svg|png|webp|ico))'");

    @Test
    void everySeededPlayerReferencesAnExistingPortrait() throws IOException {
        var paths = matches(PLAYER_IMAGE);
        assertThat(paths).hasSize(50);
        assertThat(paths).allSatisfy(this::assertFrontendAssetExists);
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
}
