package com.fantalol.backend.matchday.dto;

import com.fantalol.backend.matchday.PlayerStat;

public record PlayerStatResponse(
        Long id,
        Long matchdayId,
        Long lecPlayerId,
        String lecPlayerNickname,
        Integer kills,
        Integer morti,
        Integer assist,
        Integer cs,
        boolean vittoria,
        Integer wins,
        Double fantavoto
) {
    public static PlayerStatResponse from(PlayerStat stat) {
        return new PlayerStatResponse(
                stat.getId(), stat.getMatchday().getId(), stat.getLecPlayer().getId(), stat.getLecPlayer().getNickname(),
                stat.getKills(), stat.getMorti(), stat.getAssist(), stat.getCs(),
                stat.isVittoria(), stat.getWins(), stat.getFantavoto()
        );
    }
}
