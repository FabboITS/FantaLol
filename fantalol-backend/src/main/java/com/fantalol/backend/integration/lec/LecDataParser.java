package com.fantalol.backend.integration.lec;

import com.fasterxml.jackson.databind.JsonNode;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.PlayerRole;
import lombok.RequiredArgsConstructor;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;
import org.springframework.stereotype.Component;

import java.io.StringReader;
import java.time.Instant;
import java.time.LocalDate;
import java.util.*;

@Component
@RequiredArgsConstructor
public class LecDataParser {
    private final GameScoreCalculator scoreCalculator;

    public LecDataSnapshot parse(JsonNode pandaMatches, String oracleCsv, String league, String split) {
        List<LecDataSnapshot.Standing> standings = parseStandings(pandaMatches);
        List<PlayerRow> rows = parsePlayerRows(oracleCsv, league, split);
        return new LecDataSnapshot(
                "fresh",
                Instant.now(),
                standings.isEmpty(),
                standings,
                buildPerformances(rows),
                buildMatches(rows)
        );
    }

    public LecDataSnapshot project(
            JsonNode pandaMatches,
            List<ProviderPlayerGameStat> persistedStats,
            String status,
            Instant lastUpdatedAt
    ) {
        List<LecDataSnapshot.Standing> standings = parseStandings(pandaMatches);
        List<PlayerRow> rows = persistedStats.stream()
                .filter(ProviderPlayerGameStat::isCurrentSourceVersion)
                .filter(this::participated)
                .filter(stat -> stat.getProviderGame() != null && stat.getProviderGame().getPlayedAt() != null)
                .map(this::persistedRow)
                .toList();
        return new LecDataSnapshot(
                status,
                lastUpdatedAt,
                standings.isEmpty() || rows.isEmpty(),
                standings,
                buildPerformances(rows),
                buildMatches(rows));
    }

    public List<LecDataSnapshot.Standing> parseStandings(JsonNode matches) {
        Map<String, TeamRecord> records = new HashMap<>();
        if (matches != null && matches.isArray()) {
            for (JsonNode match : matches) {
                if (!"finished".equalsIgnoreCase(match.path("status").asText())) {
                    continue;
                }
                long winnerId = match.path("winner_id").asLong(-1);
                for (JsonNode entry : match.path("opponents")) {
                    JsonNode team = entry.path("opponent");
                    long teamId = team.path("id").asLong(-2);
                    String name = team.path("name").asText("");
                    if (!name.isBlank()) {
                        TeamRecord record = records.computeIfAbsent(name, ignored -> new TeamRecord());
                        if (teamId == winnerId) {
                            record.wins++;
                        } else {
                            record.losses++;
                        }
                    }
                }
            }
        }
        List<Map.Entry<String, TeamRecord>> ordered = new ArrayList<>(records.entrySet());
        ordered.sort(Comparator
                .<Map.Entry<String, TeamRecord>>comparingInt(entry -> entry.getValue().wins).reversed()
                .thenComparingInt(entry -> entry.getValue().losses)
                .thenComparing(Map.Entry::getKey, String.CASE_INSENSITIVE_ORDER));
        List<LecDataSnapshot.Standing> result = new ArrayList<>();
        for (int index = 0; index < ordered.size(); index++) {
            Map.Entry<String, TeamRecord> entry = ordered.get(index);
            result.add(new LecDataSnapshot.Standing(
                    index + 1, entry.getKey(), entry.getValue().wins, entry.getValue().losses));
        }
        return List.copyOf(result);
    }

    private List<PlayerRow> parsePlayerRows(String csv, String league, String split) {
        if (csv == null || csv.isBlank()) {
            return List.of();
        }
        try {
            Iterable<CSVRecord> records = CSVFormat.DEFAULT.builder()
                    .setHeader()
                    .setSkipHeaderRecord(true)
                    .setTrim(true)
                    .build()
                    .parse(new StringReader(csv));
            List<PlayerRow> rows = new ArrayList<>();
            for (CSVRecord record : records) {
                if (!league.equalsIgnoreCase(value(record, "league"))
                        || !split.equalsIgnoreCase(value(record, "split"))
                        || !"complete".equalsIgnoreCase(value(record, "datacompleteness"))) {
                    continue;
                }
                PlayerRole role = role(value(record, "position"));
                if (role == null) {
                    continue;
                }
                int kills = integer(record, "kills");
                int deaths = integer(record, "deaths");
                int assists = integer(record, "assists");
                int cs = integer(record, "total cs");
                int visionScore = integer(record, "visionscore");
                boolean win = integer(record, "result") == 1;
                rows.add(new PlayerRow(
                        value(record, "gameid"),
                        value(record, "playername"),
                        value(record, "teamname"),
                        role,
                        value(record, "champion"),
                        kills,
                        deaths,
                        assists,
                        cs,
                        visionScore,
                        scoreCalculator.calculate(role, kills, deaths, assists, cs, visionScore, win),
                        date(record)
                ));
            }
            return List.copyOf(rows);
        } catch (Exception exception) {
            throw new IllegalArgumentException("Unable to parse Oracle's Elixir CSV", exception);
        }
    }

    private List<LecDataSnapshot.PlayerPerformance> buildPerformances(List<PlayerRow> rows) {
        Map<String, List<PlayerRow>> byPlayer = new LinkedHashMap<>();
        rows.forEach(row -> byPlayer.computeIfAbsent(row.nickname.toLowerCase(Locale.ROOT),
                ignored -> new ArrayList<>()).add(row));
        List<LecDataSnapshot.PlayerPerformance> result = new ArrayList<>();
        for (List<PlayerRow> playerRows : byPlayer.values()) {
            PlayerRow first = playerRows.get(0);
            Map<String, Long> championCounts = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
            playerRows.stream().filter(row -> !row.champion.isBlank()).forEach(row ->
                    championCounts.merge(row.champion, 1L, Long::sum));
            List<LecDataSnapshot.ChampionPick> champions = championCounts.entrySet().stream()
                    .map(entry -> new LecDataSnapshot.ChampionPick(
                            entry.getKey(), championPath(entry.getKey()), entry.getValue().intValue()))
                    .toList();
            result.add(new LecDataSnapshot.PlayerPerformance(
                    first.nickname,
                    first.teamName,
                    first.role.name(),
                    playerRows.size(),
                    playerRows.stream().mapToDouble(row -> row.fantasyScore).average().orElse(0.0),
                    champions
            ));
        }
        result.sort(Comparator.comparingDouble(LecDataSnapshot.PlayerPerformance::fantasyAverage).reversed());
        return List.copyOf(result);
    }

    private List<LecDataSnapshot.MatchSummary> buildMatches(List<PlayerRow> rows) {
        Map<String, List<PlayerRow>> byGame = new LinkedHashMap<>();
        rows.forEach(row -> byGame.computeIfAbsent(row.gameId, ignored -> new ArrayList<>()).add(row));
        List<LecDataSnapshot.MatchSummary> result = new ArrayList<>();
        for (Map.Entry<String, List<PlayerRow>> entry : byGame.entrySet()) {
            List<PlayerRow> gameRows = entry.getValue();
            Set<String> teams = new LinkedHashSet<>();
            gameRows.forEach(row -> teams.add(row.teamName));
            List<LecDataSnapshot.GamePlayer> players = gameRows.stream().map(this::gamePlayer).toList();
            LocalDate date = gameRows.stream().map(row -> row.date).filter(Objects::nonNull)
                    .findFirst().orElse(null);
            String name = teams.stream().filter(team -> !team.isBlank()).reduce((left, right) -> left + " vs " + right)
                    .orElse(entry.getKey());
            LecDataSnapshot.GameSummary game = new LecDataSnapshot.GameSummary(
                    entry.getKey(), "Game " + (result.size() + 1), players);
            result.add(new LecDataSnapshot.MatchSummary(
                    entry.getKey(), name, date, "complete", List.of(game)));
        }
        result.sort(Comparator.comparing(LecDataSnapshot.MatchSummary::date,
                Comparator.nullsLast(Comparator.reverseOrder())));
        return List.copyOf(result);
    }

    private LecDataSnapshot.GamePlayer gamePlayer(PlayerRow row) {
        boolean perfectKda = row.deaths == 0;
        Double kda = perfectKda ? null : (row.kills + row.assists) / (double) row.deaths;
        return new LecDataSnapshot.GamePlayer(
                row.nickname, row.teamName, row.role.name(), row.champion, championPath(row.champion),
                row.kills, row.deaths, row.assists, row.cs, row.visionScore, kda, perfectKda);
    }

    private PlayerRow persistedRow(ProviderPlayerGameStat stat) {
        return new PlayerRow(
                stat.getProviderGame().getExternalGameId(),
                stat.getLecPlayer().getNickname(),
                stat.getSourceTeamName(),
                stat.getSourceRole(),
                stat.getSourceChampion(),
                value(stat.getCorrectedKills(), stat.getRawKills()),
                value(stat.getCorrectedDeaths(), stat.getRawDeaths()),
                value(stat.getCorrectedAssists(), stat.getRawAssists()),
                value(stat.getCorrectedCs(), stat.getRawCs()),
                value(stat.getCorrectedVisionScore(), stat.getRawVisionScore()),
                stat.getFantasyScore(),
                stat.getProviderGame().getPlayedAt()
                        .atZone(java.time.ZoneId.of("Europe/Rome"))
                        .toLocalDate());
    }

    private boolean participated(ProviderPlayerGameStat stat) {
        return stat.getCorrectedParticipated() != null
                ? stat.getCorrectedParticipated()
                : stat.isRawParticipated();
    }

    private static int value(Integer corrected, int provider) {
        return corrected == null ? provider : corrected;
    }

    private static String championPath(String championName) {
        String id = championName.replaceAll("[^A-Za-z0-9]", "");
        return id.isBlank()
                ? "/Player_immage/Champions/unknown.svg"
                : "/Player_immage/Champions/" + id + ".png";
    }

    private static PlayerRole role(String position) {
        return switch (position.toLowerCase(Locale.ROOT)) {
            case "top" -> PlayerRole.TOP;
            case "jng", "jungle" -> PlayerRole.JUNGLE;
            case "mid" -> PlayerRole.MID;
            case "bot", "adc" -> PlayerRole.ADC;
            case "sup", "support" -> PlayerRole.SUPPORT;
            default -> null;
        };
    }

    private static LocalDate date(CSVRecord record) {
        String value = value(record, "date");
        return value.isBlank() ? null : LocalDate.parse(value.substring(0, Math.min(10, value.length())));
    }

    private static String value(CSVRecord record, String column) {
        return record.isMapped(column) ? Optional.ofNullable(record.get(column)).orElse("").trim() : "";
    }

    private static int integer(CSVRecord record, String column) {
        String value = value(record, column);
        return value.isBlank() ? 0 : (int) Double.parseDouble(value);
    }

    private static final class TeamRecord {
        private int wins;
        private int losses;
    }

    private record PlayerRow(
            String gameId,
            String nickname,
            String teamName,
            PlayerRole role,
            String champion,
            int kills,
            int deaths,
            int assists,
            int cs,
            int visionScore,
            double fantasyScore,
            LocalDate date
    ) {
    }
}
