package com.fantalol.backend.scoring.dto;

import com.fantalol.backend.team.PlayerRole;

import java.time.Instant;
import java.util.List;

public record LecInsightsResponse(
        String competition,
        String formulaVersion,
        String dataStatus,
        Instant updatedAt,
        List<RoleFormula> formula,
        List<TeamStanding> standings,
        List<PlayerPerformance> players
) {
    public record RoleFormula(PlayerRole role, double kills, double assists, double deaths,
                              double csPerHundred, double winBonus) {}

    public record TeamStanding(int rank, String teamName, String logoUrl, int gamesPlayed,
                               double totalScore, double averageScore) {}

    public record PlayerPerformance(int rank, Long playerId, String nickname, PlayerRole role,
                                    String teamName, String imageUrl, int gamesPlayed,
                                    int kills, int deaths, int assists, int cs, int wins,
                                    double totalScore, double averageScore) {}
}
