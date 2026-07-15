package com.fantalol.backend.league.dto;

import com.fantalol.backend.league.League;

public record LeagueResponse(
        Long id,
        String nome,
        String codiceInvito,
        Integer creditiIniziali,
        String adminUsername,
        int numeroSquadre
) {
    public static LeagueResponse from(League league) {
        int numeroSquadre = league.getFantaTeams() == null ? 0 : league.getFantaTeams().size();
        return new LeagueResponse(league.getId(), league.getNome(), league.getCodiceInvito(),
                league.getCreditiIniziali(), league.getAdmin().getUsername(), numeroSquadre);
    }
}
