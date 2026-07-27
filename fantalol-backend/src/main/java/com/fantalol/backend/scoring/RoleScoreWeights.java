package com.fantalol.backend.scoring;

import com.fantalol.backend.team.PlayerRole;

import java.util.EnumMap;
import java.util.Map;

public final class RoleScoreWeights {
    private static final Map<PlayerRole, Weights> VALUES = new EnumMap<>(PlayerRole.class);

    static {
        VALUES.put(PlayerRole.TOP, new Weights(3.00, 2.00, 2.00, 1.25));
        VALUES.put(PlayerRole.JUNGLE, new Weights(3.00, 2.25, 2.00, 0.70));
        VALUES.put(PlayerRole.MID, new Weights(3.00, 2.00, 2.00, 1.00));
        VALUES.put(PlayerRole.ADC, new Weights(3.25, 1.75, 2.25, 1.10));
        VALUES.put(PlayerRole.SUPPORT, new Weights(2.15, 2.55, 1.75, 0.20));
    }

    private RoleScoreWeights() {
    }

    public static Weights forRole(PlayerRole role) {
        if (role == null) {
            throw new IllegalArgumentException("Player role is required");
        }
        return VALUES.get(role);
    }

    public record Weights(double kills, double assists, double deaths, double csPerHundred) {
    }
}
