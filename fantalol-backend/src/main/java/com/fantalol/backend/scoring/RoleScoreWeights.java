package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;

import java.util.EnumMap;
import java.util.Map;

/**
 * Frozen Summer 2026 v1 coefficients. They deliberately stay close to the
 * legacy 3/2/-2/+1 formula while compensating for role-specific stat profiles.
 */
public final class RoleScoreWeights {
    public static final String FORMULA_VERSION = "SUMMER_2026_V1";
    private static final Map<PlayerRole, Weights> VALUES = new EnumMap<>(PlayerRole.class);

    static {
        VALUES.put(PlayerRole.TOP, new Weights(3.00, 2.00, 2.00, 1.10));
        VALUES.put(PlayerRole.JUNGLE, new Weights(3.00, 2.25, 2.00, 0.70));
        VALUES.put(PlayerRole.MID, new Weights(3.00, 2.00, 2.00, 1.00));
        VALUES.put(PlayerRole.ADC, new Weights(3.25, 1.75, 2.00, 1.20));
        VALUES.put(PlayerRole.SUPPORT, new Weights(2.50, 2.50, 2.00, 0.20));
    }

    private RoleScoreWeights() {
    }

    public static Weights forRole(PlayerRole role) {
        return VALUES.get(role);
    }

    public record Weights(double kills, double assists, double deaths, double csPerHundred) {
    }
}
