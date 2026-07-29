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

    public boolean isSuccessfulImport() {
        return acceptedGames() > 0 && failedGames == 0 && unmatchedPlayers.isEmpty();
    }

    public int diagnosticFailedGames() {
        return Math.max(1, failedGames);
    }

    public String failureMessage() {
        if (acceptedGames() == 0) {
            return "Oracle import contained no usable complete LEC Summer games";
        }
        if (unmatchedPlayers.isEmpty()) {
            return "Oracle import rejected " + diagnosticFailedGames() + " game(s)";
        }
        return "Oracle import rejected " + diagnosticFailedGames()
                + " game(s); unmatched players: " + String.join(", ", unmatchedPlayers);
    }

    private int acceptedGames() {
        return insertedGames + updatedGames + skippedGames;
    }
}
