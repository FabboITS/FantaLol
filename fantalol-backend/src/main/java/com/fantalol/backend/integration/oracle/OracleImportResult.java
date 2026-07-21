package com.fantalol.backend.integration.oracle;

import java.util.List;

public record OracleImportResult(
        int importedGames,
        int skippedGames,
        int importedPlayerRows,
        List<String> unmatchedPlayers
) {
}
