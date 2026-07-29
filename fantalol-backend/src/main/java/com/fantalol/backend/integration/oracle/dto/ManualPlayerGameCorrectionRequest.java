package com.fantalol.backend.integration.oracle.dto;

import jakarta.validation.constraints.Min;

public record ManualPlayerGameCorrectionRequest(
        Boolean participated,
        @Min(0)
        Integer kills,
        @Min(0)
        Integer deaths,
        @Min(0)
        Integer assists,
        @Min(0)
        Integer cs,
        @Min(0)
        Integer visionScore,
        Boolean win
) {
}
