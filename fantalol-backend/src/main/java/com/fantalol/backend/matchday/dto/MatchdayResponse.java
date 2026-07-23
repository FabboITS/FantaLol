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
        boolean chiusa,
        String status,
        boolean auctionLocked,
        boolean formationLocked,
        java.time.Instant formationLockedAt,
        String formationLockedBy,
        String scoringStatus,
        boolean provisional
) {
    public static MatchdayResponse from(Matchday matchday) {
        return new MatchdayResponse(matchday.getId(), matchday.getLeague().getId(), matchday.getLeague().getNome(), matchday.getNumero(), matchday.getDescrizione(),
                matchday.getData(), matchday.isChiusa(), (matchday.getStatus() != null ? matchday.getStatus() : (matchday.isChiusa() ? com.fantalol.backend.matchday.MatchdayStatus.CLOSED : com.fantalol.backend.matchday.MatchdayStatus.OPEN)).name(),
                !matchday.isChiusa() && matchday.getLeague().isAuctionOpen(),
                matchday.isFormationLocked(), matchday.getFormationLockedAt(), matchday.getFormationLockedBy(),
                matchday.isChiusa() ? "LEGACY_COMPLETE" : "PROVISIONAL", !matchday.isChiusa());
    }

    public MatchdayResponse withScoringStatus(String scoringStatus) {
        return new MatchdayResponse(id, leagueId, leagueNome, numero, descrizione, data, chiusa, status,
                auctionLocked, formationLocked, formationLockedAt, formationLockedBy, scoringStatus,
                !"COMPLETE".equals(scoringStatus) && !"LEGACY_COMPLETE".equals(scoringStatus));
    }
}
