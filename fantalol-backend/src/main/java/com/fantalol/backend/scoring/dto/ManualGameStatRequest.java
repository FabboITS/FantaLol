package com.fantalol.backend.scoring.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;

public record ManualGameStatRequest(
        @NotBlank String externalSeriesId,
        @NotBlank String externalGameId,
        @NotNull @Min(1) Integer gameNumber,
        String stage,
        String teamOne,
        String teamTwo,
        Instant scheduledAt,
        @NotEmpty List<Long> matchdayIds,
        @NotNull Long playerId,
        @NotNull @Min(0) Integer kills,
        @NotNull @Min(0) Integer deaths,
        @NotNull @Min(0) Integer assists,
        @NotNull @Min(0) Integer cs,
        boolean win
) {
}
