package com.fantalol.backend.team.dto;

import com.fantalol.backend.team.LecTeam;

import java.util.List;

public record LecTeamResponse(
        Long id,
        String nome,
        String sigla,
        String logoUrl,
        List<LecPlayerResponse> giocatori
) {
    public static LecTeamResponse from(LecTeam team) {
        List<LecPlayerResponse> giocatori = team.getGiocatori() == null ? List.of() :
                team.getGiocatori().stream().map(LecPlayerResponse::fromWithoutTeam).toList();
        return new LecTeamResponse(team.getId(), team.getNome(), team.getSigla(), team.getLogoUrl(), giocatori);
    }

    public static LecTeamResponse summaryFrom(LecTeam team) {
        return new LecTeamResponse(team.getId(), team.getNome(), team.getSigla(), team.getLogoUrl(), null);
    }
}
