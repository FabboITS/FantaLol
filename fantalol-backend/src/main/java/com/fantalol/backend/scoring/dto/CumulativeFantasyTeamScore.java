package com.fantalol.backend.scoring.dto;

import java.util.List;

public record CumulativeFantasyTeamScore(
        Long fantasyTeamId,
        String teamName,
        List<FantasyRoleSlotScore> slots,
        Double overallTotal,
        boolean provisional
) {
}
