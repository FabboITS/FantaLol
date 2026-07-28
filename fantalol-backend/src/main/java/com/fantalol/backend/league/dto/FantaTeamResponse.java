package com.fantalol.backend.league.dto;

import com.fantalol.backend.league.FantaTeam;

import java.util.List;

public record FantaTeamResponse(
        Long id,
        String nome,
        Integer creditiResidui,
        Long leagueId,
        String leagueNome,
        String ownerUsername,
        Double punti,
        List<RosterEntryResponse> rosa
) {
    public static FantaTeamResponse from(FantaTeam team) {
        return from(team, team.getPunti() != null ? team.getPunti() : 0.0);
    }

    public static FantaTeamResponse from(FantaTeam team, Double punti) {
        List<RosterEntryResponse> rosa = team.getRosa() == null ? List.of() :
                team.getRosa().stream().map(RosterEntryResponse::from).toList();
        return new FantaTeamResponse(team.getId(), team.getNome(), team.getCreditiResidui(),
                team.getLeague().getId(), team.getLeague().getNome(), team.getOwner().getUsername(),
                punti, rosa);
    }
}
