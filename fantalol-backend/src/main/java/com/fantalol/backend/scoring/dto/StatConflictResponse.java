package com.fantalol.backend.scoring.dto;

import com.fantalol.backend.scoring.PlayerGameStat;
import com.fantalol.backend.scoring.StatSource;

public record StatConflictResponse(
        Long id,
        String externalGameId,
        Long playerId,
        String playerNickname,
        StatSource effectiveSource,
        Candidate oracle,
        Candidate manual
) {
    public static StatConflictResponse from(PlayerGameStat stat) {
        return new StatConflictResponse(stat.getId(), stat.getGame().getExternalId(), stat.getPlayer().getId(),
                stat.getPlayer().getNickname(), stat.getEffectiveSource(),
                new Candidate(stat.getOracleKills(), stat.getOracleDeaths(), stat.getOracleAssists(),
                        stat.getOracleCs(), stat.getOracleWin()),
                new Candidate(stat.getManualKills(), stat.getManualDeaths(), stat.getManualAssists(),
                        stat.getManualCs(), stat.getManualWin()));
    }

    public record Candidate(Integer kills, Integer deaths, Integer assists, Integer cs, Boolean win) {
    }
}
