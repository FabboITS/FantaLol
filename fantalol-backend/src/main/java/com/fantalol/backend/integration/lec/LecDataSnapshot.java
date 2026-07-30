package com.fantalol.backend.integration.lec;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

public record LecDataSnapshot(
        String status,
        Instant lastUpdatedAt,
        boolean provisional,
        List<Standing> standings,
        List<PlayerPerformance> performances,
        List<MatchSummary> matches
) {
    public static LecDataSnapshot empty() {
        return new LecDataSnapshot("awaiting-data", null, true, List.of(), List.of(), List.of());
    }

    public record Standing(int position, String teamName, int seriesWins, int seriesLosses) {
    }

    public record ChampionPick(String championName, String imagePath, int pickCount) {
    }

    public record PlayerPerformance(
            String nickname,
            String teamName,
            String role,
            int gamesPlayed,
            double fantasyAverage,
            List<ChampionPick> champions
    ) {
    }

    public record MatchSummary(
            String id,
            String name,
            LocalDate date,
            String status,
            List<GameSummary> games
    ) {
    }

    public record GameSummary(String id, String label, List<GamePlayer> players) {
    }

    public record GamePlayer(
            String nickname,
            String teamName,
            String role,
            String championName,
            String championImagePath,
            int kills,
            int deaths,
            int assists,
            int cs,
            int visionScore,
            Double kda,
            boolean perfectKda,
            Double fantasyScore
    ) {
    }
}
