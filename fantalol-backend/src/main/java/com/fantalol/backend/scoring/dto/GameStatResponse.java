package com.fantalol.backend.scoring.dto;

import com.fantalol.backend.scoring.PlayerGameStat;
import com.fantalol.backend.scoring.RoleScoreWeights;
import com.fantalol.backend.scoring.GameScoreCalculator;
import com.fantalol.backend.scoring.StatSource;

public record GameStatResponse(
        Long id,
        Long gameId,
        String externalGameId,
        Long playerId,
        String playerNickname,
        StatSource effectiveSource,
        boolean conflict,
        Integer kills,
        Integer deaths,
        Integer assists,
        Integer cs,
        Boolean win,
        Double score,
        String formulaVersion
) {
    public static GameStatResponse from(PlayerGameStat stat, GameScoreCalculator calculator) {
        return new GameStatResponse(stat.getId(), stat.getGame().getId(), stat.getGame().getExternalId(),
                stat.getPlayer().getId(), stat.getPlayer().getNickname(), stat.getEffectiveSource(), stat.isConflict(),
                stat.effectiveKills(), stat.effectiveDeaths(), stat.effectiveAssists(), stat.effectiveCs(),
                stat.effectiveWin(), calculator.calculate(stat), RoleScoreWeights.FORMULA_VERSION);
    }
}
