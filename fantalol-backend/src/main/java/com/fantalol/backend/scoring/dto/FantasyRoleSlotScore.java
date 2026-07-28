package com.fantalol.backend.scoring.dto;

import com.fantalol.backend.team.PlayerRole;

import java.util.List;

public record FantasyRoleSlotScore(
        PlayerRole role,
        int gamesPlayed,
        Double average,
        List<String> contributingPlayers,
        String status
) {
}
