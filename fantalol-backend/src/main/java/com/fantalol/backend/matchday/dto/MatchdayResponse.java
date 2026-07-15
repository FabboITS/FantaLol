package com.fantalol.backend.matchday.dto;

import com.fantalol.backend.matchday.Matchday;

import java.time.LocalDate;

public record MatchdayResponse(
        Long id,
        Long leagueId,
        String leagueNome,
        Integer numero,
        String descrizione,
        LocalDate data,
        boolean chiusa
) {
    public static MatchdayResponse from(Matchday matchday) {
        return new MatchdayResponse(matchday.getId(), matchday.getLeague().getId(), matchday.getLeague().getNome(), matchday.getNumero(), matchday.getDescrizione(),
                matchday.getData(), matchday.isChiusa());
    }
}
