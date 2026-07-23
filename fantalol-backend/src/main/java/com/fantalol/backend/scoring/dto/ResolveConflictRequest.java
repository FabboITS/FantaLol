package com.fantalol.backend.scoring.dto;

import com.fantalol.backend.scoring.StatSource;
import jakarta.validation.constraints.NotNull;

public record ResolveConflictRequest(@NotNull StatSource source) {
}
