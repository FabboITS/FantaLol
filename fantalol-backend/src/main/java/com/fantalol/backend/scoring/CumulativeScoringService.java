package com.fantalol.backend.scoring;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStatRepository;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.lineup.EffectiveLineupPeriod;
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
        return scoreTeams(List.of(team)).get(0);
    }

    @Transactional(readOnly = true)
    public List<CumulativeFantasyTeamScore> leagueRanking(Long leagueId) {
        List<FantaTeam> teams = fantaTeamRepository.findByLeagueId(leagueId);
        if (teams.isEmpty()) {
            return List.of();
        }
        return scoreTeams(teams).stream()
                .sorted(Comparator.comparing(CumulativeFantasyTeamScore::overallTotal,
                        Comparator.nullsLast(Comparator.reverseOrder()))
                        .thenComparing(CumulativeFantasyTeamScore::teamName))
                .toList();
    }

    private List<CumulativeFantasyTeamScore> scoreTeams(List<FantaTeam> teams) {
        Map<Long, FantaTeam> teamsById = teams.stream()
                .collect(Collectors.toMap(FantaTeam::getId, team -> team));
        Map<Long, Map<PlayerRole, SlotAccumulator>> slotsByTeam = teams.stream()
                .collect(Collectors.toMap(FantaTeam::getId, ignored -> emptySlots()));
        List<EffectiveLineupPeriod> periods = lineupPeriodRepository.findByFantaTeamIdIn(teamsById.keySet());
        Map<Long, List<EffectiveLineupPeriod>> periodsByPlayer = periods.stream()
                .collect(Collectors.groupingBy(period -> period.getLecPlayer().getId()));

        for (ProviderPlayerGameStat stat : observations()) {
            Instant playedAt = stat.getProviderGame().getPlayedAt();
            for (EffectiveLineupPeriod period : periodsByPlayer
                    .getOrDefault(stat.getLecPlayer().getId(), List.of())) {
                Long teamId = period.getFantaTeam().getId();
                if (teamsById.containsKey(teamId) && activeAt(period, playedAt)) {
                    slotsByTeam.get(teamId).get(period.getRole()).add(stat);
                }
            }
        }

        return teams.stream()
                .map(team -> fantasyTeamScore(team, slotsByTeam.get(team.getId())))
                .toList();
    }

    private Map<PlayerRole, SlotAccumulator> emptySlots() {
        Map<PlayerRole, SlotAccumulator> slots = new EnumMap<>(PlayerRole.class);
        for (PlayerRole role : PlayerRole.values()) {
            slots.put(role, new SlotAccumulator());
        }
        return slots;
    }

    private boolean activeAt(EffectiveLineupPeriod period, Instant playedAt) {
        return !period.getEffectiveFrom().isAfter(playedAt)
                && (period.getEffectiveUntil() == null || period.getEffectiveUntil().isAfter(playedAt));
    }

    private CumulativeFantasyTeamScore fantasyTeamScore(
            FantaTeam team,
            Map<PlayerRole, SlotAccumulator> slots) {
        List<FantasyRoleSlotScore> projections = slots.entrySet().stream()
                .map(entry -> entry.getValue().toScore(entry.getKey()))
                .toList();
        boolean provisional = projections.stream().anyMatch(slot -> slot.gamesPlayed() == 0);
        Double overallTotal = provisional ? null : slots.values().stream()
                .mapToDouble(SlotAccumulator::total)
                .sum();
        return new CumulativeFantasyTeamScore(team.getId(), team.getNome(), projections, overallTotal, provisional);
    }

    private CumulativePlayerScore playerScore(List<ProviderPlayerGameStat> playerStats) {
        LecPlayer player = playerStats.get(0).getLecPlayer();
        double average = playerStats.stream().mapToDouble(ProviderPlayerGameStat::getFantasyScore).average().orElseThrow();
        return new CumulativePlayerScore(player.getId(), player.getNickname(), player.getRuolo(),
                playerStats.size(), average, "available");
    }

    private List<ProviderPlayerGameStat> observations() {
        return statRepository.findAllByOrderByProviderGamePlayedAtAsc().stream()
                .filter(ProviderPlayerGameStat::isActiveSourceVersion)
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

        double total() {
            return scores.stream().mapToDouble(Double::doubleValue).sum();
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
