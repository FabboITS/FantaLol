package com.fantalol.backend.scoring.dto;

import com.fantalol.backend.team.PlayerRole;

public record CumulativePlayerScore(
        Long playerId,
        String nickname,
        PlayerRole role,
        int gamesPlayed,
        Double average,
        String status
) {
}
