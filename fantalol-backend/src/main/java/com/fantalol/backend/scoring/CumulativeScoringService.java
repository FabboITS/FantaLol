package com.fantalol.backend.scoring;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStatRepository;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.lineup.EffectiveLineupPeriodRepository;
import com.fantalol.backend.scoring.dto.CumulativeFantasyTeamScore;
import com.fantalol.backend.scoring.dto.CumulativePlayerScore;
import com.fantalol.backend.scoring.dto.FantasyRoleSlotScore;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class CumulativeScoringService {

    private final ProviderPlayerGameStatRepository statRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final EffectiveLineupPeriodRepository lineupPeriodRepository;

    @Transactional(readOnly = true)
    public List<CumulativePlayerScore> playerScores() {
        return observations().stream()
                .collect(Collectors.groupingBy(stat -> stat.getLecPlayer().getId()))
                .values().stream()
                .map(this::playerScore)
                .sorted(Comparator.comparing(CumulativePlayerScore::average).reversed()
                        .thenComparing(CumulativePlayerScore::nickname))
                .toList();
    }

    @Transactional(readOnly = true)
    public CumulativePlayerScore playerScore(Long playerId) {
        List<ProviderPlayerGameStat> playerStats = observations().stream()
                .filter(stat -> stat.getLecPlayer().getId().equals(playerId))
                .toList();
        if (playerStats.isEmpty()) {
            throw new ResourceNotFoundException("Nessuna statistica disponibile per il player con id: " + playerId);
        }
        return playerScore(playerStats);
    }

    @Transactional(readOnly = true)
    public CumulativeFantasyTeamScore teamScore(Long fantasyTeamId) {
        FantaTeam team = fantaTeamRepository.findById(fantasyTeamId)
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata con id: " + fantasyTeamId));
        Map<PlayerRole, SlotAccumulator> slots = new EnumMap<>(PlayerRole.class);
        for (PlayerRole role : PlayerRole.values()) {
            slots.put(role, new SlotAccumulator());
        }

        for (ProviderPlayerGameStat stat : observations()) {
            Instant playedAt = stat.getProviderGame().getPlayedAt();
            PlayerRole role = stat.getLecPlayer().getRuolo();
            lineupPeriodRepository.findActiveByFantaTeamIdAndRole(fantasyTeamId, role, playedAt)
                    .filter(period -> period.getLecPlayer().getId().equals(stat.getLecPlayer().getId()))
                    .ifPresent(ignored -> slots.get(role).add(stat));
        }

        List<FantasyRoleSlotScore> projections = slots.entrySet().stream()
                .map(entry -> entry.getValue().toScore(entry.getKey()))
                .toList();
        boolean provisional = projections.stream().anyMatch(slot -> slot.gamesPlayed() == 0);
        Double overallAverage = provisional ? null : projections.stream()
                .mapToDouble(FantasyRoleSlotScore::average)
                .average()
                .orElseThrow();
        return new CumulativeFantasyTeamScore(team.getId(), team.getNome(), projections, overallAverage, provisional);
    }

    @Transactional(readOnly = true)
    public List<CumulativeFantasyTeamScore> leagueRanking(Long leagueId) {
        return fantaTeamRepository.findByLeagueId(leagueId).stream()
                .map(team -> teamScore(team.getId()))
                .sorted(Comparator.comparing(CumulativeFantasyTeamScore::overallAverage,
                        Comparator.nullsLast(Comparator.reverseOrder()))
                        .thenComparing(CumulativeFantasyTeamScore::teamName))
                .toList();
    }

    private CumulativePlayerScore playerScore(List<ProviderPlayerGameStat> playerStats) {
        LecPlayer player = playerStats.get(0).getLecPlayer();
        double average = playerStats.stream().mapToDouble(ProviderPlayerGameStat::getFantasyScore).average().orElseThrow();
        return new CumulativePlayerScore(player.getId(), player.getNickname(), player.getRuolo(),
                playerStats.size(), average, "available");
    }

    private List<ProviderPlayerGameStat> observations() {
        return statRepository.findAllByOrderByProviderGamePlayedAtAsc().stream()
                .filter(this::participated)
                .filter(stat -> stat.getProviderGame() != null && stat.getProviderGame().getPlayedAt() != null)
                .toList();
    }

    private boolean participated(ProviderPlayerGameStat stat) {
        return stat.getCorrectedParticipated() != null
                ? stat.getCorrectedParticipated()
                : stat.isRawParticipated();
    }

    private static class SlotAccumulator {
        private final List<Double> scores = new ArrayList<>();
        private final Set<String> players = new LinkedHashSet<>();

        void add(ProviderPlayerGameStat stat) {
            scores.add(stat.getFantasyScore());
            players.add(stat.getLecPlayer().getNickname());
        }

        FantasyRoleSlotScore toScore(PlayerRole role) {
            if (scores.isEmpty()) {
                return new FantasyRoleSlotScore(role, 0, null, List.of(), "awaiting-data");
            }
            double average = scores.stream().mapToDouble(Double::doubleValue).average().orElseThrow();
            return new FantasyRoleSlotScore(role, scores.size(), average, List.copyOf(players), "available");
        }
    }
}
