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
        Double confirmedPoints,
        Double provisionalPoints,
        List<RosterEntryResponse> rosa
) {
    public static FantaTeamResponse from(FantaTeam team) {
        List<RosterEntryResponse> rosa = team.getRosa() == null ? List.of() :
                team.getRosa().stream().map(RosterEntryResponse::from).toList();
        return new FantaTeamResponse(team.getId(), team.getNome(), team.getCreditiResidui(),
                team.getLeague().getId(), team.getLeague().getNome(), team.getOwner().getUsername(),
                value(team.getPunti()), value(team.getConfirmedPoints()), value(team.getProvisionalPoints()), rosa);
    }

    private static double value(Double value) {
        return value != null ? value : 0.0;
    }
}
