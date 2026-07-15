package com.fantalol.backend.team.dto;

import com.fantalol.backend.team.LecPlayer;

public record LecPlayerResponse(
        Long id,
        String nickname,
        String nomeReale,
        String nazionalita,
        String ruolo,
        Integer quotazione,
        Long teamId,
        String teamNome
) {
    public static LecPlayerResponse from(LecPlayer player) {
        return new LecPlayerResponse(
                player.getId(), player.getNickname(), player.getNomeReale(), player.getNazionalita(),
                player.getRuolo().name(), player.getQuotazione(),
                player.getTeam() != null ? player.getTeam().getId() : null,
                player.getTeam() != null ? player.getTeam().getNome() : null
        );
    }

    /** Usata quando il player viene incluso dentro la risposta del team, per evitare ricorsione infinita. */
    public static LecPlayerResponse fromWithoutTeam(LecPlayer player) {
        return new LecPlayerResponse(
                player.getId(), player.getNickname(), player.getNomeReale(), player.getNazionalita(),
                player.getRuolo().name(), player.getQuotazione(), null, null
        );
    }
}
