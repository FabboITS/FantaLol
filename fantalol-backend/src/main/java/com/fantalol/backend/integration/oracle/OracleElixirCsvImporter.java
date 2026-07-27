package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.matchday.*;
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
import java.util.*;

@Service
@RequiredArgsConstructor
public class OracleElixirCsvImporter {
    private static final String PROVIDER = "ORACLES_ELIXIR";

    private final MatchdayRepository matchdayRepository;
    private final PlayerStatRepository playerStatRepository;
    private final ImportedGameRepository importedGameRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final FantaScoreCalculator scoreCalculator;

    @Transactional
    public OracleImportResult importCsv(Long matchdayId, MultipartFile file, String league, String split) {
        Matchday matchday = matchdayRepository.findById(matchdayId)
                .orElseThrow(() -> new BusinessRuleException("Matchday not found: " + matchdayId));
        if (matchday.isChiusa()) {
            throw new BusinessRuleException("Closed matchdays cannot receive imported statistics");
        }
        if (file == null || file.isEmpty()) {
            throw new BusinessRuleException("A non-empty Oracle's Elixir CSV file is required");
        }

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            Iterable<CSVRecord> records = CSVFormat.DEFAULT.builder()
                    .setHeader()
                    .setSkipHeaderRecord(true)
                    .setTrim(true)
                    .build()
                    .parse(reader);

            Map<String, List<CSVRecord>> byGame = new LinkedHashMap<>();
            for (CSVRecord record : records) {
                if (!equalsIgnoreCase(record, "league", league)
                        || !equalsIgnoreCase(record, "split", split)
                        || !"complete".equalsIgnoreCase(value(record, "datacompleteness"))) {
                    continue;
                }
                String position = value(record, "position");
                if (!Set.of("top", "jng", "mid", "bot", "sup").contains(position.toLowerCase(Locale.ROOT))) {
                    continue;
                }
                String gameId = value(record, "gameid");
                if (!gameId.isBlank()) {
                    byGame.computeIfAbsent(gameId, ignored -> new ArrayList<>()).add(record);
                }
            }

            int importedGames = 0;
            int skippedGames = 0;
            int importedRows = 0;
            Set<String> unmatched = new TreeSet<>(String.CASE_INSENSITIVE_ORDER);

            for (Map.Entry<String, List<CSVRecord>> entry : byGame.entrySet()) {
                String gameId = entry.getKey();
                if (importedGameRepository.existsByProviderAndExternalGameId(PROVIDER, gameId)) {
                    skippedGames++;
                    continue;
                }

                List<ResolvedRow> resolvedRows = new ArrayList<>();
                for (CSVRecord record : entry.getValue()) {
                    Optional<LecPlayer> player = resolvePlayer(record);
                    if (player.isEmpty()) {
                        unmatched.add(value(record, "playername"));
                        continue;
                    }
                    resolvedRows.add(new ResolvedRow(player.get(), record));
                }

                if (resolvedRows.size() != entry.getValue().size()) {
                    continue;
                }

                for (ResolvedRow row : resolvedRows) {
                    PlayerStat stat = playerStatRepository
                            .findByMatchdayIdAndLecPlayerId(matchdayId, row.player().getId())
                            .orElse(PlayerStat.builder()
                                    .matchday(matchday)
                                    .lecPlayer(row.player())
                                    .gamesPlayed(0)
                                    .build());
                    stat.setKills(stat.getKills() + integer(row.record(), "kills"));
                    stat.setMorti(stat.getMorti() + integer(row.record(), "deaths"));
                    stat.setAssist(stat.getAssist() + integer(row.record(), "assists"));
                    stat.setCs(stat.getCs() + integer(row.record(), "total cs"));
                    int currentWins = stat.getWins() != null ? stat.getWins() : (stat.isVittoria() ? 1 : 0);
                    stat.setWins(currentWins + integer(row.record(), "result"));
                    int currentGames = stat.getGamesPlayed() != null ? stat.getGamesPlayed() : 0;
                    stat.setGamesPlayed(currentGames + 1);
                    stat.setVittoria(stat.getWins() > 0);
                    stat.setFantavoto(scoreCalculator.calculate(stat));
                    playerStatRepository.save(stat);
                    importedRows++;
                }

                importedGameRepository.save(ImportedGame.builder()
                        .provider(PROVIDER)
                        .externalGameId(gameId)
                        .matchday(matchday)
                        .build());
                importedGames++;
            }

            return new OracleImportResult(importedGames, skippedGames, importedRows, List.copyOf(unmatched));
        } catch (BusinessRuleException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new BusinessRuleException("Unable to import Oracle's Elixir CSV: " + exception.getMessage());
        }
    }

    private Optional<LecPlayer> resolvePlayer(CSVRecord record) {
        String externalId = value(record, "playerid");
        if (!externalId.isBlank()) {
            Optional<LecPlayer> byExternalId = lecPlayerRepository.findByOraclePlayerId(externalId);
            if (byExternalId.isPresent()) {
                return byExternalId;
            }
        }
        Optional<LecPlayer> byNickname = lecPlayerRepository.findFirstByNicknameIgnoreCase(value(record, "playername"));
        byNickname.ifPresent(player -> {
            if (!externalId.isBlank() && player.getOraclePlayerId() == null) {
                player.setOraclePlayerId(externalId);
                lecPlayerRepository.save(player);
            }
        });
        return byNickname;
    }

    private static boolean equalsIgnoreCase(CSVRecord record, String column, String expected) {
        return expected == null || expected.isBlank() || expected.equalsIgnoreCase(value(record, column));
    }

    private static String value(CSVRecord record, String column) {
        return record.isMapped(column) ? Optional.ofNullable(record.get(column)).orElse("").trim() : "";
    }

    private static int integer(CSVRecord record, String column) {
        String value = value(record, column);
        return value.isBlank() ? 0 : (int) Double.parseDouble(value);
    }

    private record ResolvedRow(LecPlayer player, CSVRecord record) {
    }
}
