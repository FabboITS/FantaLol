package com.fantalol.backend.matchday.dto;

import com.fantalol.backend.team.PlayerRole;

public record FormationPlayerResponse(
        Long id,
        String nickname,
        PlayerRole role,
        Double matchdayScore
) {}
