package com.fantalol.backend.scoring;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.team.LecPlayer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class MatchdayScoringEngine {
    private final MatchdaySeriesRepository matchdaySeriesRepository;
    private final OfficialGameRepository officialGameRepository;
    private final PlayerGameStatRepository playerGameStatRepository;
    private final FormationRepository formationRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final GameScoreCalculator calculator;

    @Transactional(readOnly = true)
    public double playerMatchdayScore(Long matchdayId, Long playerId) {
        return matchdaySeriesRepository.findByMatchdayId(matchdayId).stream()
                .mapToDouble(link -> playerSeriesScore(link.getSeries().getId(), playerId))
                .sum();
    }

    @Transactional(readOnly = true)
    public boolean usesGameScoring(Long matchdayId) {
        return !matchdaySeriesRepository.findByMatchdayId(matchdayId).isEmpty();
    }

    @Transactional(readOnly = true)
    public double playerSeriesScore(Long seriesId, Long playerId) {
        List<PlayerGameStat> appearances = playerGameStatRepository.findByGameSeriesIdAndPlayerId(seriesId, playerId)
                .stream()
                .filter(stat -> stat.getEffectiveSource() != null)
                .toList();
        return appearances.isEmpty() ? 0.0
                : appearances.stream().mapToDouble(calculator::calculate).average().orElse(0.0);
    }

    @Transactional
    public void recomputeForSeries(Long seriesId) {
        matchdaySeriesRepository.findBySeriesId(seriesId)
                .forEach(link -> recomputeMatchday(link.getMatchday().getId()));
    }

    @Transactional
    public void recomputeMatchday(Long matchdayId) {
        for (Formation formation : formationRepository.findByMatchdayId(matchdayId)) {
            double playerTotal = formation.getTitolari().stream()
                    .mapToDouble(player -> playerMatchdayScore(matchdayId, player.getId()))
                    .sum();
            double teamScore = formation.getTitolari().isEmpty() ? 0.0 : playerTotal / 5.0;
            formation.setPunteggioTotale(teamScore);
            formation.setFormulaVersion(RoleScoreWeights.FORMULA_VERSION);
            formationRepository.save(formation);
            recomputeTeamTotal(formation.getFantaTeam());
        }
    }

    @Transactional(readOnly = true)
    public ScoringDataStatus status(Long matchdayId) {
        var links = matchdaySeriesRepository.findByMatchdayId(matchdayId);
        if (links.isEmpty()) return ScoringDataStatus.EMPTY;
        if (links.stream().anyMatch(link ->
                playerGameStatRepository.countByGameSeriesIdAndConflictTrue(link.getSeries().getId()) > 0)) {
            return ScoringDataStatus.CONFLICT;
        }
        boolean anyStats = links.stream().anyMatch(link ->
                playerGameStatRepository.countByGameSeriesId(link.getSeries().getId()) > 0);
        if (!anyStats) return ScoringDataStatus.EMPTY;
        boolean complete = links.stream().allMatch(link -> {
            var games = officialGameRepository.findBySeriesIdOrderByGameNumber(link.getSeries().getId());
            return link.getSeries().isCompleted()
                    && !games.isEmpty()
                    && games.stream().allMatch(game ->
                    playerGameStatRepository.countByGameIdAndEffectiveSourceIsNotNull(game.getId()) >= 10);
        });
        return complete ? ScoringDataStatus.COMPLETE : ScoringDataStatus.PROVISIONAL;
    }

    void recomputeTeamTotal(FantaTeam team) {
        if (team.getLegacyPoints() == null) {
            team.setLegacyPoints(team.getPunti() != null ? team.getPunti() : 0.0);
        }
        var summerFormations = formationRepository.findByFantaTeamId(team.getId()).stream()
                .filter(formation -> RoleScoreWeights.FORMULA_VERSION.equals(formation.getFormulaVersion()))
                .filter(formation -> formation.getPunteggioTotale() != null)
                .toList();
        double confirmedSummer = summerFormations.stream()
                .filter(formation -> formation.getMatchday().isChiusa())
                .map(Formation::getPunteggioTotale)
                .mapToDouble(Double::doubleValue)
                .sum();
        double provisional = summerFormations.stream()
                .filter(formation -> !formation.getMatchday().isChiusa())
                .map(Formation::getPunteggioTotale)
                .mapToDouble(Double::doubleValue)
                .sum();
        double confirmed = team.getLegacyPoints() + confirmedSummer;
        team.setConfirmedPoints(confirmed);
        team.setProvisionalPoints(provisional);
        team.setPunti(confirmed + provisional);
        fantaTeamRepository.save(team);
    }
}
