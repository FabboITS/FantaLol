package com.fantalol.backend.matchday.dto;

import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.matchday.FormationSource;
import com.fantalol.backend.team.LecPlayer;

import java.util.List;
import java.util.Map;

public record FormationResponse(
        Long id,
        Long fantaTeamId,
        Long matchdayId,
        List<String> titolari,
        List<FormationPlayerResponse> players,
        FormationSource source,
        Double punteggioTotale
) {
    public static FormationResponse from(Formation formation) {
        return from(formation, Map.of());
    }

    public static FormationResponse from(Formation formation, Map<Long, Double> scores) {
        List<String> titolari = formation.getTitolari().stream().map(LecPlayer::getNickname).toList();
        List<FormationPlayerResponse> players = formation.getTitolari().stream()
                .map(player -> new FormationPlayerResponse(player.getId(), player.getNickname(), player.getRuolo(),
                        scores.getOrDefault(player.getId(), 0.0)))
                .toList();
        return new FormationResponse(formation.getId(), formation.getFantaTeam().getId(), formation.getMatchday().getId(),
                titolari, players, formation.getSource(), formation.getPunteggioTotale());
    }
}
