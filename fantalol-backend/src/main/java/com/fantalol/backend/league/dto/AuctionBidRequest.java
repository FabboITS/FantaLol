package com.fantalol.backend.league.dto;

import jakarta.validation.constraints.*;

public record AuctionBidRequest(
        @NotNull Long fantaTeamId,
        @NotNull @Positive Integer credits
) {}
