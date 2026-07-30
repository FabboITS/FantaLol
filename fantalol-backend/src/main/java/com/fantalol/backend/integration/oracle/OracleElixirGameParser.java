package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.team.PlayerRole;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

@Component
public class OracleElixirGameParser {
    private static final int PLAYERS_PER_GAME = 10;
    private static final char FINGERPRINT_SEPARATOR = '\u001f';
    private static final String SUPPORTED_LEAGUE = "LEC";
    private static final String SUPPORTED_SPLIT = "Summer";

    public List<OracleGameBatch> parse(String csv, String league, String split) {
        if (csv == null || csv.isBlank()
                || !SUPPORTED_LEAGUE.equalsIgnoreCase(league)
                || !SUPPORTED_SPLIT.equalsIgnoreCase(split)) {
            return List.of();
        }

        Map<String, List<ParsedPlayerRow>> rowsByGame = new LinkedHashMap<>();
        String normalizedCsv = csv.startsWith("\uFEFF") ? csv.substring(1) : csv;
        try (CSVParser records = CSVFormat.DEFAULT.builder()
                .setHeader()
                .setSkipHeaderRecord(true)
                .setTrim(true)
                .build()
                .parse(new StringReader(normalizedCsv))) {
            for (CSVRecord record : records) {
                parseEligibleRow(record).ifPresent(row ->
                        rowsByGame.computeIfAbsent(row.externalGameId(), ignored -> new ArrayList<>()).add(row));
            }
        } catch (IOException exception) {
            throw new IllegalArgumentException("Unable to parse Oracle's Elixir CSV", exception);
        }

        return rowsByGame.values().stream()
                .filter(rows -> rows.size() == PLAYERS_PER_GAME)
                .map(this::toGameBatch)
                .toList();
    }

    private Optional<ParsedPlayerRow> parseEligibleRow(CSVRecord record) {
        if (!SUPPORTED_LEAGUE.equalsIgnoreCase(value(record, "league"))
                || !SUPPORTED_SPLIT.equalsIgnoreCase(value(record, "split"))
                || !"complete".equalsIgnoreCase(value(record, "datacompleteness"))) {
            return Optional.empty();
        }

        String externalGameId = value(record, "gameid");
        Optional<PlayerRole> role = playerRole(value(record, "position"));
        Optional<Instant> playedAt = parseInstant(value(record, "date"));
        if (externalGameId.isBlank() || role.isEmpty() || playedAt.isEmpty()) {
            return Optional.empty();
        }

        OraclePlayerGameRow player = new OraclePlayerGameRow(
                value(record, "playerid"),
                value(record, "playername"),
                value(record, "teamname"),
                role.get(),
                value(record, "champion"),
                integer(record, "kills"),
                integer(record, "deaths"),
                integer(record, "assists"),
                integer(record, "total cs"),
                integer(record, "visionscore"),
                integer(record, "result") == 1);
        return Optional.of(new ParsedPlayerRow(externalGameId, playedAt.get(), player));
    }

    private OracleGameBatch toGameBatch(List<ParsedPlayerRow> rows) {
        ParsedPlayerRow firstRow = rows.get(0);
        List<OraclePlayerGameRow> players = rows.stream().map(ParsedPlayerRow::player).toList();
        return new OracleGameBatch(
                firstRow.externalGameId(),
                firstRow.playedAt(),
                players,
                fingerprint(firstRow.externalGameId(), firstRow.playedAt(), players));
    }

    private static String value(CSVRecord record, String column) {
        return record.isMapped(column) ? Optional.ofNullable(record.get(column)).orElse("").trim() : "";
    }

    private static int integer(CSVRecord record, String column) {
        String value = value(record, column);
        return value.isBlank() ? 0 : (int) Double.parseDouble(value);
    }

    private static Optional<PlayerRole> playerRole(String position) {
        return switch (position.toLowerCase(Locale.ROOT)) {
            case "top" -> Optional.of(PlayerRole.TOP);
            case "jng", "jungle" -> Optional.of(PlayerRole.JUNGLE);
            case "mid", "middle" -> Optional.of(PlayerRole.MID);
            case "bot", "adc", "bottom" -> Optional.of(PlayerRole.ADC);
            case "sup", "support" -> Optional.of(PlayerRole.SUPPORT);
            default -> Optional.empty();
        };
    }

    private static Optional<Instant> parseInstant(String value) {
        if (value.isBlank()) {
            return Optional.empty();
        }
        try {
            return Optional.of(Instant.parse(value));
        } catch (RuntimeException ignored) {
            try {
                return Optional.of(OffsetDateTime.parse(value).toInstant());
            } catch (RuntimeException ignoredAgain) {
                try {
                    return Optional.of(LocalDateTime.parse(value, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
                            .toInstant(ZoneOffset.UTC));
                } catch (RuntimeException ignoredOnceMore) {
                    return Optional.empty();
                }
            }
        }
    }

    private static String fingerprint(String externalGameId, Instant playedAt, List<OraclePlayerGameRow> players) {
        String normalizedRows = players.stream()
                .map(OracleElixirGameParser::normalizedPlayerRow)
                .sorted(Comparator.naturalOrder())
                .reduce(normalize(externalGameId) + FINGERPRINT_SEPARATOR + playedAt + "\n",
                        (fingerprint, row) -> fingerprint + row + "\n");
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(normalizedRows.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static String normalizedPlayerRow(OraclePlayerGameRow player) {
        return String.join(String.valueOf(FINGERPRINT_SEPARATOR),
                normalize(player.externalPlayerId()),
                normalize(player.nickname()),
                normalize(player.teamName()),
                player.role().name(),
                normalize(player.champion()),
                String.valueOf(player.kills()),
                String.valueOf(player.deaths()),
                String.valueOf(player.assists()),
                String.valueOf(player.cs()),
                String.valueOf(player.visionScore()),
                String.valueOf(player.win()));
    }

    private static String normalize(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private record ParsedPlayerRow(String externalGameId, Instant playedAt, OraclePlayerGameRow player) {
    }
}
