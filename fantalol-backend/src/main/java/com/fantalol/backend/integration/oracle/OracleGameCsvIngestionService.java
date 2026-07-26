package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.scoring.*;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import lombok.RequiredArgsConstructor;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.util.*;

@Service
@RequiredArgsConstructor
public class OracleGameCsvIngestionService {
    private static final String PROVIDER = "ORACLES_ELIXIR";

    private final OfficialSeriesRepository seriesRepository;
    private final OfficialGameRepository gameRepository;
    private final MatchdaySeriesRepository matchdaySeriesRepository;
    private final com.fantalol.backend.matchday.MatchdayRepository matchdayRepository;
    private final LecPlayerRepository playerRepository;
    private final GameStatService gameStatService;
    private final MatchdayScoringEngine scoringEngine;
    private final com.fantalol.backend.matchday.FormationService formationService;

    @Transactional
    public void importCsv(Long matchdayId, MultipartFile file, String league, String split) {
        var targetMatchday = matchdayRepository.findById(matchdayId)
                .orElseThrow(() -> new com.fantalol.backend.common.ResourceNotFoundException(
                        "Giornata non trovata con id: " + matchdayId));
        formationService.ensureEffectiveFormations(targetMatchday);
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            Iterable<CSVRecord> records = CSVFormat.DEFAULT.builder()
                    .setHeader()
                    .setSkipHeaderRecord(true)
                    .setTrim(true)
                    .build()
                    .parse(reader);
            Map<String, List<CSVRecord>> byGame = new LinkedHashMap<>();
            for (CSVRecord record : records) {
                if (!matches(record, "league", league) || !matches(record, "split", split)
                        || !"complete".equalsIgnoreCase(value(record, "datacompleteness"))) continue;
                if (targetMatchday.getData() != null && !sameCompetitionWeek(record, targetMatchday.getData())) continue;
                if (!Set.of("top", "jng", "mid", "bot", "sup")
                        .contains(value(record, "position").toLowerCase(Locale.ROOT))) continue;
                String gameId = value(record, "gameid");
                if (!gameId.isBlank()) byGame.computeIfAbsent(gameId, ignored -> new ArrayList<>()).add(record);
            }
            Set<Long> changedSeries = new HashSet<>();
            for (var gameRows : byGame.entrySet()) {
                List<ResolvedRow> rows = resolveAll(gameRows.getValue());
                if (rows.size() != gameRows.getValue().size()) continue;
                OfficialSeries series = findOrCreateSeries(gameRows.getKey(), gameRows.getValue());
                link(matchdayId, series);
                OfficialGame game = gameRepository.findByProviderAndExternalId(PROVIDER, gameRows.getKey())
                        .orElseGet(() -> gameRepository.save(OfficialGame.builder()
                                .provider(PROVIDER)
                                .externalId(gameRows.getKey())
                                .series(series)
                                .gameNumber(gameNumber(gameRows.getValue().get(0)))
                                .playedAt(playedAt(gameRows.getValue().get(0)))
                                .build()));
                for (ResolvedRow row : rows) {
                    gameStatService.submitOracle(game, row.player(), value(row.record(), "teamname"),
                            integer(row.record(), "kills"),
                            integer(row.record(), "deaths"), integer(row.record(), "assists"),
                            integer(row.record(), "total cs"), integer(row.record(), "result") > 0);
                }
                series.setCompleted(true);
                seriesRepository.save(series);
                changedSeries.add(series.getId());
            }
            changedSeries.forEach(scoringEngine::recomputeForSeries);
        } catch (Exception exception) {
            throw new com.fantalol.backend.common.BusinessRuleException(
                    "Unable to import game-level Oracle's Elixir data: " + exception.getMessage());
        }
    }

    private List<ResolvedRow> resolveAll(List<CSVRecord> records) {
        List<ResolvedRow> resolved = new ArrayList<>();
        for (CSVRecord record : records) {
            Optional<LecPlayer> player = resolvePlayer(record);
            player.ifPresent(value -> resolved.add(new ResolvedRow(value, record)));
        }
        return resolved;
    }

    private Optional<LecPlayer> resolvePlayer(CSVRecord record) {
        String externalId = value(record, "playerid");
        if (!externalId.isBlank()) {
            var result = playerRepository.findByOraclePlayerId(externalId);
            if (result.isPresent()) return result;
        }
        return playerRepository.findFirstByNicknameIgnoreCase(value(record, "playername"));
    }

    private OfficialSeries findOrCreateSeries(String gameId, List<CSVRecord> rows) {
        CSVRecord first = rows.get(0);
        List<String> teams = rows.stream().map(row -> value(row, "teamname"))
                .filter(name -> !name.isBlank()).distinct().sorted(String.CASE_INSENSITIVE_ORDER).toList();
        String date = value(first, "date");
        String seriesExternalId = teams.size() == 2 && !date.isBlank()
                ? date + ":" + teams.get(0) + ":" + teams.get(1)
                : "GAME:" + gameId;
        Instant playedAt = playedAt(first);
        if (teams.size() == 2 && playedAt != null) {
            Optional<OfficialSeries> scheduled = seriesRepository.findAll().stream()
                    .filter(series -> "PANDASCORE".equals(series.getProvider()))
                    .filter(series -> series.getScheduledAt() != null)
                    .filter(series -> Math.abs(Duration.between(series.getScheduledAt(), playedAt).toHours()) <= 24)
                    .filter(series -> sameTeams(series, teams))
                    .findFirst();
            if (scheduled.isPresent()) return scheduled.get();
        }
        return seriesRepository.findByProviderAndExternalId(PROVIDER, seriesExternalId)
                .orElseGet(() -> seriesRepository.save(OfficialSeries.builder()
                        .provider(PROVIDER).externalId(seriesExternalId)
                        .stage(value(first, "playoffs").equals("1") ? "PLAYOFFS" : "REGULAR")
                        .teamOne(teams.size() > 0 ? teams.get(0) : null)
                        .teamTwo(teams.size() > 1 ? teams.get(1) : null)
                        .scheduledAt(playedAt(first)).build()));
    }

    private static boolean sameTeams(OfficialSeries series, List<String> teams) {
        Set<String> expected = Set.of(normalizeTeam(teams.get(0)), normalizeTeam(teams.get(1)));
        Set<String> actual = Set.of(normalizeTeam(series.getTeamOne()), normalizeTeam(series.getTeamTwo()));
        return expected.equals(actual);
    }

    private static String normalizeTeam(String value) {
        return value == null ? "" : value.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
    }

    private void link(Long matchdayId, OfficialSeries series) {
        if (matchdaySeriesRepository.existsByMatchdayIdAndSeriesId(matchdayId, series.getId())) return;
        var matchday = matchdayRepository.findById(matchdayId)
                .orElseThrow(() -> new com.fantalol.backend.common.ResourceNotFoundException(
                        "Giornata non trovata con id: " + matchdayId));
        matchdaySeriesRepository.save(MatchdaySeries.builder().matchday(matchday).series(series).build());
    }

    private static int gameNumber(CSVRecord row) {
        int number = integer(row, "game");
        return number > 0 ? number : 1;
    }

    private static Instant playedAt(CSVRecord row) {
        String raw = value(row, "date");
        if (raw.isBlank()) return null;
        try {
            return OffsetDateTime.parse(raw).toInstant();
        } catch (DateTimeException ignored) {
            try {
                return LocalDateTime.parse(raw.replace(" ", "T")).toInstant(ZoneOffset.UTC);
            } catch (DateTimeException second) {
                try {
                    return LocalDate.parse(raw.substring(0, Math.min(raw.length(), 10))).atStartOfDay(ZoneOffset.UTC).toInstant();
                } catch (DateTimeException third) {
                    return null;
                }
            }
        }
    }

    private static boolean matches(CSVRecord record, String column, String expected) {
        return expected == null || expected.isBlank() || expected.equalsIgnoreCase(value(record, column));
    }

    private static boolean sameCompetitionWeek(CSVRecord record, LocalDate target) {
        String raw = value(record, "date");
        if (raw.length() < 10) return false;
        try {
            LocalDate actual = LocalDate.parse(raw.substring(0, 10));
            var weekFields = java.time.temporal.WeekFields.ISO;
            return actual.get(weekFields.weekBasedYear()) == target.get(weekFields.weekBasedYear())
                    && actual.get(weekFields.weekOfWeekBasedYear()) == target.get(weekFields.weekOfWeekBasedYear());
        } catch (DateTimeException exception) {
            return false;
        }
    }

    private static String value(CSVRecord record, String column) {
        return record.isMapped(column) ? Optional.ofNullable(record.get(column)).orElse("").trim() : "";
    }

    private static int integer(CSVRecord record, String column) {
        String raw = value(record, column);
        return raw.isBlank() ? 0 : (int) Double.parseDouble(raw);
    }

    private record ResolvedRow(LecPlayer player, CSVRecord record) {
    }
}
