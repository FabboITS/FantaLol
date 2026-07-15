package com.fantalol.backend.league.dto;

import com.fantalol.backend.league.RosterEntry;

import java.time.Instant;

public record RosterEntryResponse(
        Long id,
        Long lecPlayerId,
        String lecPlayerNickname,
        String ruolo,
        Integer creditiSpesi,
        Instant dataAcquisto
) {
    public static RosterEntryResponse from(RosterEntry entry) {
        return new RosterEntryResponse(
                entry.getId(),
                entry.getLecPlayer().getId(),
                entry.getLecPlayer().getNickname(),
                entry.getLecPlayer().getRuolo().name(),
                entry.getCreditiSpesi(),
                entry.getDataAcquisto()
        );
    }
}
