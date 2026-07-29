package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.team.PlayerRole;

public record OraclePlayerGameRow(
        String externalPlayerId,
        String nickname,
        String teamName,
        PlayerRole role,
        String champion,
        int kills,
        int deaths,
        int assists,
        int cs,
        int visionScore,
        boolean win
) {
}
