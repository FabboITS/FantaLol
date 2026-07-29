package com.fantalol.backend.integration.oracle;

import java.time.Instant;
import java.util.List;

public record OracleGameBatch(
        String externalGameId,
        Instant playedAt,
        List<OraclePlayerGameRow> players,
        String sourceFingerprint
) {
    public OracleGameBatch {
        players = List.copyOf(players);
    }
}
