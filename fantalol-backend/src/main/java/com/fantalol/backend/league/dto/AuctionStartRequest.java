package com.fantalol.backend.league.dto;

import jakarta.validation.constraints.NotNull;

public record AuctionStartRequest(@NotNull Long leagueId, @NotNull Long lecPlayerId,
                                  @NotNull Long fantaTeamId) {}
