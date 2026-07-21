package com.fantalol.backend.league.dto;

import com.fantalol.backend.league.League;

public record LeagueResponse(
        Long id,
        String nome,
        String codiceInvito,
        Integer creditiIniziali,
        String adminUsername,
        int numeroSquadre,
        boolean auctionOpen,
        Integer participantCount,
        boolean competitionStarted,
        int maxRosterSize,
        int maxPerRole
) {
    public static LeagueResponse from(League league) {
        int numeroSquadre = league.getFantaTeams() == null ? 0 : league.getFantaTeams().size();
        int policyCount = league.getParticipantCount() != null ? league.getParticipantCount() : numeroSquadre;
        boolean smallLeague = policyCount <= 5;
        return new LeagueResponse(league.getId(), league.getNome(), league.getCodiceInvito(),
                league.getCreditiIniziali(), league.getAdmin().getUsername(), numeroSquadre,
                league.isAuctionOpen(), league.getParticipantCount(), league.isCompetitionStarted(),
                smallLeague ? 10 : 5, smallLeague ? 2 : 1);
    }
}
