package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;

@Service
@RequiredArgsConstructor
class OracleGameImportPersistenceService {
    private static final String ORACLE_PROVIDER = ProviderGame.ORACLES_ELIXIR;

    private final ProviderGameRepository providerGameRepository;
    private final ProviderPlayerGameStatRepository playerGameStatRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final GameScoreCalculator gameScoreCalculator;

    @Transactional
    public OracleImportSummary importBatches(List<OracleGameBatch> batches, String league, String split) {
        ImportCounts counts = new ImportCounts();
        Set<String> unmatchedPlayers = new TreeSet<>(String.CASE_INSENSITIVE_ORDER);
        for (OracleGameBatch batch : batches) {
            importBatch(batch, league, split, counts, unmatchedPlayers);
        }
        return new OracleImportSummary(
                counts.insertedGames,
                counts.updatedGames,
                counts.skippedGames,
                counts.failedGames,
                new ArrayList<>(unmatchedPlayers));
    }

    private void importBatch(
            OracleGameBatch batch,
            String league,
            String split,
            ImportCounts counts,
            Set<String> unmatchedPlayers
    ) {
        List<ResolvedRow> resolvedRows = resolveRows(batch.players(), unmatchedPlayers);
        if (resolvedRows.size() != batch.players().size()) {
            counts.failedGames++;
            return;
        }

        Optional<ProviderGame> existing = providerGameRepository
                .findByProviderAndExternalGameId(ORACLE_PROVIDER, batch.externalGameId());
        if (existing.isPresent() && batch.sourceFingerprint().equals(existing.get().getSourceFingerprint())) {
            counts.skippedGames++;
            return;
        }

        if (existing.isEmpty()) {
            ProviderGame game = ProviderGame.builder()
                    .provider(ORACLE_PROVIDER)
                    .externalGameId(batch.externalGameId())
                    .playedAt(batch.playedAt())
                    .league(league)
                    .split(split)
                    .sourceFingerprint(batch.sourceFingerprint())
                    .build();
            ProviderGame savedGame = providerGameRepository.save(game);
            resolvedRows.forEach(row -> playerGameStatRepository.save(newProviderStat(savedGame, row, batch.sourceFingerprint())));
            counts.insertedGames++;
            return;
        }

        ProviderGame game = existing.get();
        game.setPlayedAt(batch.playedAt());
        game.setLeague(league);
        game.setSplit(split);
        game.setSourceFingerprint(batch.sourceFingerprint());
        game.setSourceLastSeenAt(Instant.now());
        providerGameRepository.save(game);

        Map<Long, ProviderPlayerGameStat> existingStatsByPlayer = new HashMap<>();
        for (ProviderPlayerGameStat stat : playerGameStatRepository.findByProviderGameId(game.getId())) {
            existingStatsByPlayer.put(stat.getLecPlayer().getId(), stat);
        }
        for (ResolvedRow row : resolvedRows) {
            ProviderPlayerGameStat stat = existingStatsByPlayer.get(row.player().getId());
            if (stat == null) {
                playerGameStatRepository.save(newProviderStat(game, row, batch.sourceFingerprint()));
                continue;
            }
            updateProviderSnapshot(stat, row, batch.sourceFingerprint());
            if (!stat.isOverridden()) {
                stat.setFantasyScore(score(row));
            }
            playerGameStatRepository.save(stat);
        }
        counts.updatedGames++;
    }

    private List<ResolvedRow> resolveRows(List<OraclePlayerGameRow> rows, Set<String> unmatchedPlayers) {
        List<ResolvedRow> resolved = new ArrayList<>();
        Set<Long> resolvedPlayerIds = new HashSet<>();
        for (OraclePlayerGameRow row : rows) {
            Optional<LecPlayer> player = resolvePlayer(row);
            if (player.isPresent() && resolvedPlayerIds.add(player.get().getId())) {
                resolved.add(new ResolvedRow(player.get(), row));
            } else {
                unmatchedPlayers.add(row.nickname());
            }
        }
        return resolved;
    }

    private Optional<LecPlayer> resolvePlayer(OraclePlayerGameRow row) {
        if (row.externalPlayerId() != null && !row.externalPlayerId().isBlank()) {
            Optional<LecPlayer> byOracleId = lecPlayerRepository
                    .findFirstByOraclePlayerIdIgnoreCase(row.externalPlayerId());
            if (byOracleId.isPresent()) {
                return byOracleId;
            }
        }
        return lecPlayerRepository.findFirstByNicknameIgnoreCase(row.nickname());
    }

    private ProviderPlayerGameStat newProviderStat(
            ProviderGame game,
            ResolvedRow row,
            String sourceFingerprint
    ) {
        ProviderPlayerGameStat stat = ProviderPlayerGameStat.builder()
                .providerGame(game)
                .lecPlayer(row.player())
                .overridden(false)
                .build();
        updateProviderSnapshot(stat, row, sourceFingerprint);
        stat.setFantasyScore(score(row));
        return stat;
    }

    private void updateProviderSnapshot(
            ProviderPlayerGameStat stat,
            ResolvedRow row,
            String sourceFingerprint
    ) {
        OraclePlayerGameRow source = row.source();
        stat.setExternalPlayerId(source.externalPlayerId());
        stat.setSourceNickname(source.nickname());
        stat.setSourceTeamName(source.teamName());
        stat.setSourceRole(source.role());
        stat.setSourceChampion(source.champion());
        stat.setSourceFingerprint(sourceFingerprint);
        stat.setRawParticipated(true);
        stat.setRawKills(source.kills());
        stat.setRawDeaths(source.deaths());
        stat.setRawAssists(source.assists());
        stat.setRawCs(source.cs());
        stat.setRawVisionScore(source.visionScore());
        stat.setRawWin(source.win());
    }

    private double score(ResolvedRow row) {
        OraclePlayerGameRow source = row.source();
        return gameScoreCalculator.calculate(
                source.role(),
                source.kills(),
                source.deaths(),
                source.assists(),
                source.cs(),
                source.visionScore(),
                source.win());
    }

    private record ResolvedRow(LecPlayer player, OraclePlayerGameRow source) {
    }

    private static final class ImportCounts {
        private int insertedGames;
        private int updatedGames;
        private int skippedGames;
        private int failedGames;
    }
}
