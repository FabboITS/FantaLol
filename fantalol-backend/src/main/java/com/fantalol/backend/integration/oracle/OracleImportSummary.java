package com.fantalol.backend.integration.oracle;

import java.util.List;

public record OracleImportSummary(
        int insertedGames,
        int updatedGames,
        int skippedGames,
        int failedGames,
        List<String> unmatchedPlayers
) {
    public OracleImportSummary {
        unmatchedPlayers = List.copyOf(unmatchedPlayers);
    }
}
