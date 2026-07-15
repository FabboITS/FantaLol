package com.fantalol.backend.matchday.dto;

import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.team.LecPlayer;

import java.util.List;

public record FormationResponse(
        Long id,
        Long fantaTeamId,
        Long matchdayId,
        List<String> titolari,
        String capitano,
        Double punteggioTotale
) {
    public static FormationResponse from(Formation formation) {
        List<String> titolari = formation.getTitolari().stream().map(LecPlayer::getNickname).toList();
        String capitano = formation.getCapitano() != null ? formation.getCapitano().getNickname() : null;
        return new FormationResponse(formation.getId(), formation.getFantaTeam().getId(), formation.getMatchday().getId(),
                titolari, capitano, formation.getPunteggioTotale());
    }
}
