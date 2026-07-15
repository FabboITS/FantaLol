package com.fantalol.backend.matchday.dto;

import com.fantalol.backend.matchday.PlayerStat;

public record PlayerStatResponse(
        Long id,
        Long matchdayId,
        Long lecPlayerId,
        String lecPlayerNickname,
        Double votoBase,
        Integer kills,
        Integer morti,
        Integer assist,
        boolean mvp,
        boolean vittoria,
        Double fantavoto
) {
    public static PlayerStatResponse from(PlayerStat stat) {
        return new PlayerStatResponse(
                stat.getId(), stat.getMatchday().getId(), stat.getLecPlayer().getId(), stat.getLecPlayer().getNickname(),
                stat.getVotoBase(), stat.getKills(), stat.getMorti(), stat.getAssist(),
                stat.isMvp(), stat.isVittoria(), stat.getFantavoto()
        );
    }
}
