package com.fantalol.backend.scoring;

import com.fantalol.backend.scoring.dto.LecInsightsResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;

@Service
@RequiredArgsConstructor
public class LecInsightsService {
    private static final String COMPETITION = "LEC Summer 2026";

    private final PlayerGameStatRepository statRepository;
    private final OfficialGameRepository gameRepository;
    private final GameScoreCalculator calculator;

    @Transactional(readOnly = true)
    public LecInsightsResponse summer2026() {
        List<PlayerGameStat> stats = statRepository.findAll().stream()
                .filter(stat -> stat.getEffectiveSource() != null)
                .toList();
        Map<Long, LecPlayer> players = new HashMap<>();
        Map<Long, PlayerAccumulator> playerTotals = new HashMap<>();
        Map<Long, Map<String, TeamGameAccumulator>> teamGames = new HashMap<>();

        for (PlayerGameStat stat : stats) {
            LecPlayer player = stat.getPlayer();
            players.put(player.getId(), player);
            double score = calculator.calculate(stat);
            playerTotals.computeIfAbsent(player.getId(), ignored -> new PlayerAccumulator())
                    .add(stat, score);
            String teamName = teamName(stat);
            if (teamName != null) {
                teamGames.computeIfAbsent(stat.getGame().getId(), ignored -> new HashMap<>())
                        .computeIfAbsent(teamName, ignored -> new TeamGameAccumulator())
                        .add(score, player.getTeam() != null ? player.getTeam().getLogoUrl() : null);
            }
        }

        List<LecInsightsResponse.PlayerPerformance> playerRows = playerTotals.entrySet().stream()
                .map(entry -> playerRow(players.get(entry.getKey()), entry.getValue()))
                .sorted(Comparator.comparingDouble(LecInsightsResponse.PlayerPerformance::totalScore).reversed()
                        .thenComparing(Comparator.comparingDouble(LecInsightsResponse.PlayerPerformance::averageScore).reversed())
                        .thenComparing(LecInsightsResponse.PlayerPerformance::nickname, String.CASE_INSENSITIVE_ORDER))
                .toList();
        playerRows = rankPlayers(playerRows);

        Map<String, TeamAccumulator> teams = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
        teamGames.values().forEach(game -> game.forEach((name, values) ->
                teams.computeIfAbsent(name, ignored -> new TeamAccumulator()).add(values)));
        List<LecInsightsResponse.TeamStanding> standings = teams.entrySet().stream()
                .map(entry -> teamRow(entry.getKey(), entry.getValue()))
                .sorted(Comparator.comparingDouble(LecInsightsResponse.TeamStanding::totalScore).reversed()
                        .thenComparing(Comparator.comparingDouble(LecInsightsResponse.TeamStanding::averageScore).reversed())
                        .thenComparing(LecInsightsResponse.TeamStanding::teamName, String.CASE_INSENSITIVE_ORDER))
                .toList();
        standings = rankTeams(standings);

        return new LecInsightsResponse(COMPETITION, RoleScoreWeights.FORMULA_VERSION,
                dataStatus(stats), updatedAt(stats), formula(), standings, playerRows);
    }

    private String dataStatus(List<PlayerGameStat> stats) {
        if (stats.isEmpty()) return ScoringDataStatus.EMPTY.name();
        if (stats.stream().anyMatch(PlayerGameStat::isConflict)) return ScoringDataStatus.CONFLICT.name();
        var games = gameRepository.findAll();
        boolean complete = !games.isEmpty() && games.stream()
                .allMatch(game -> game.getSeries().isCompleted()
                        && statRepository.countByGameIdAndEffectiveSourceIsNotNull(game.getId()) >= 10);
        return complete ? ScoringDataStatus.COMPLETE.name() : ScoringDataStatus.PROVISIONAL.name();
    }

    private static Instant updatedAt(List<PlayerGameStat> stats) {
        return stats.stream().map(stat -> stat.getManualUpdatedAt() != null
                        && (stat.getOracleUpdatedAt() == null || stat.getManualUpdatedAt().isAfter(stat.getOracleUpdatedAt()))
                        ? stat.getManualUpdatedAt() : stat.getOracleUpdatedAt())
                .filter(Objects::nonNull).max(Instant::compareTo).orElse(null);
    }

    private static List<LecInsightsResponse.RoleFormula> formula() {
        return Arrays.stream(PlayerRole.values()).map(role -> {
            var weights = RoleScoreWeights.forRole(role);
            return new LecInsightsResponse.RoleFormula(role, weights.kills(), weights.assists(),
                    -weights.deaths(), weights.csPerHundred(), 3.0);
        }).toList();
    }

    private static String teamName(PlayerGameStat stat) {
        if (stat.getTeamNameSnapshot() != null && !stat.getTeamNameSnapshot().isBlank()) {
            return stat.getTeamNameSnapshot();
        }
        return stat.getPlayer().getTeam() != null ? stat.getPlayer().getTeam().getNome() : null;
    }

    private static LecInsightsResponse.PlayerPerformance playerRow(LecPlayer player, PlayerAccumulator values) {
        String teamName = values.latestTeam != null ? values.latestTeam
                : player.getTeam() != null ? player.getTeam().getNome() : null;
        return new LecInsightsResponse.PlayerPerformance(0, player.getId(), player.getNickname(), player.getRuolo(),
                teamName, player.getImageUrl(), values.games, values.kills, values.deaths, values.assists, values.cs, values.wins,
                values.total, values.games == 0 ? 0.0 : values.total / values.games);
    }

    private static LecInsightsResponse.TeamStanding teamRow(String name, TeamAccumulator values) {
        return new LecInsightsResponse.TeamStanding(0, name, values.logoUrl, values.games,
                values.total, values.games == 0 ? 0.0 : values.total / values.games);
    }

    private static List<LecInsightsResponse.PlayerPerformance> rankPlayers(List<LecInsightsResponse.PlayerPerformance> rows) {
        List<LecInsightsResponse.PlayerPerformance> ranked = new ArrayList<>();
        for (int i = 0; i < rows.size(); i++) {
            var row = rows.get(i);
            ranked.add(new LecInsightsResponse.PlayerPerformance(i + 1, row.playerId(), row.nickname(), row.role(),
                    row.teamName(), row.imageUrl(), row.gamesPlayed(), row.kills(), row.deaths(), row.assists(),
                    row.cs(), row.wins(), row.totalScore(), row.averageScore()));
        }
        return ranked;
    }

    private static List<LecInsightsResponse.TeamStanding> rankTeams(List<LecInsightsResponse.TeamStanding> rows) {
        List<LecInsightsResponse.TeamStanding> ranked = new ArrayList<>();
        for (int i = 0; i < rows.size(); i++) {
            var row = rows.get(i);
            ranked.add(new LecInsightsResponse.TeamStanding(i + 1, row.teamName(), row.logoUrl(), row.gamesPlayed(),
                    row.totalScore(), row.averageScore()));
        }
        return ranked;
    }

    private static final class PlayerAccumulator {
        int games, kills, deaths, assists, cs, wins;
        double total;
        String latestTeam;
        Instant latestAt;

        void add(PlayerGameStat stat, double score) {
            games++;
            kills += stat.effectiveKills();
            deaths += stat.effectiveDeaths();
            assists += stat.effectiveAssists();
            cs += stat.effectiveCs();
            if (stat.effectiveWin()) wins++;
            total += score;
            Instant playedAt = stat.getGame().getPlayedAt();
            if (latestAt == null || playedAt == null || playedAt.isAfter(latestAt)) {
                latestAt = playedAt;
                latestTeam = teamName(stat);
            }
        }
    }

    private static final class TeamGameAccumulator {
        double playerTotal;
        String logoUrl;
        void add(double score, String logo) { playerTotal += score; if (logoUrl == null) logoUrl = logo; }
    }

    private static final class TeamAccumulator {
        int games;
        double total;
        String logoUrl;
        void add(TeamGameAccumulator game) { games++; total += game.playerTotal / 5.0; if (logoUrl == null) logoUrl = game.logoUrl; }
    }
}
