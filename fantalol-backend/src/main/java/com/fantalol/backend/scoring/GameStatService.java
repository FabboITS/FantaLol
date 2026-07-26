package com.fantalol.backend.scoring;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.matchday.MatchdayRepository;
import com.fantalol.backend.scoring.dto.GameStatResponse;
import com.fantalol.backend.scoring.dto.ManualGameStatRequest;
import com.fantalol.backend.scoring.dto.StatConflictResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class GameStatService {
    private final OfficialSeriesRepository seriesRepository;
    private final OfficialGameRepository gameRepository;
    private final MatchdaySeriesRepository matchdaySeriesRepository;
    private final PlayerGameStatRepository statRepository;
    private final PlayerGameStatAuditRepository auditRepository;
    private final MatchdayRepository matchdayRepository;
    private final LecPlayerRepository playerRepository;
    private final MatchdayScoringEngine scoringEngine;
    private final GameScoreCalculator calculator;

    @Transactional
    public GameStatResponse insertManual(String actor, ManualGameStatRequest request) {
        OfficialSeries series = seriesRepository.findByProviderAndExternalId("MANUAL", request.externalSeriesId())
                .orElseGet(() -> seriesRepository.save(OfficialSeries.builder()
                        .provider("MANUAL")
                        .externalId(request.externalSeriesId())
                        .stage(request.stage())
                        .teamOne(request.teamOne())
                        .teamTwo(request.teamTwo())
                        .scheduledAt(request.scheduledAt())
                        .build()));
        OfficialGame game = gameRepository.findByProviderAndExternalId("MANUAL", request.externalGameId())
                .orElseGet(() -> gameRepository.save(OfficialGame.builder()
                        .series(series)
                        .provider("MANUAL")
                        .externalId(request.externalGameId())
                        .gameNumber(request.gameNumber())
                        .playedAt(request.scheduledAt())
                        .build()));
        linkMatchdays(series, request.matchdayIds());
        LecPlayer player = playerRepository.findById(request.playerId())
                .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + request.playerId()));
        PlayerGameStat stat = submit(game, player, currentTeamName(player), StatSource.MANUAL,
                request.kills(), request.deaths(), request.assists(), request.cs(), request.win(), actor);
        scoringEngine.recomputeForSeries(series.getId());
        return GameStatResponse.from(stat, calculator);
    }

    @Transactional
    public PlayerGameStat submitOracle(OfficialGame game, LecPlayer player, String teamName, int kills,
                                       int deaths, int assists, int cs, boolean win) {
        return submit(game, player, teamName, StatSource.ORACLE, kills, deaths, assists, cs, win,
                "ORACLE_SYNC");
    }

    @Transactional(readOnly = true)
    public List<StatConflictResponse> conflicts() {
        return statRepository.findByConflictTrueOrderByGamePlayedAtDesc().stream()
                .map(StatConflictResponse::from)
                .toList();
    }

    @Transactional
    public GameStatResponse resolve(Long id, StatSource source, String actor) {
        PlayerGameStat stat = statRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Conflitto statistiche non trovato: " + id));
        if (!stat.isConflict()) {
            throw new BusinessRuleException("La statistica non ha un conflitto aperto");
        }
        try {
            stat.resolve(source);
        } catch (IllegalStateException exception) {
            throw new BusinessRuleException(exception.getMessage());
        }
        statRepository.save(stat);
        auditRepository.save(audit(stat, "RESOLVE", source, actor));
        scoringEngine.recomputeForSeries(stat.getGame().getSeries().getId());
        return GameStatResponse.from(stat, calculator);
    }

    private PlayerGameStat submit(OfficialGame game, LecPlayer player, String teamName, StatSource source,
                                  int kills, int deaths, int assists, int cs, boolean win, String actor) {
        PlayerGameStat stat = statRepository.findByGameIdAndPlayerId(game.getId(), player.getId())
                .orElse(PlayerGameStat.builder().game(game).player(player).build());
        if (teamName != null && !teamName.isBlank()) stat.setTeamNameSnapshot(teamName.trim());
        else if (stat.getTeamNameSnapshot() == null) stat.setTeamNameSnapshot(currentTeamName(player));
        stat.submit(source, kills, deaths, assists, cs, win, actor);
        statRepository.save(stat);
        auditRepository.save(audit(stat, "SUBMIT", source, actor));
        return stat;
    }

    private static String currentTeamName(LecPlayer player) {
        return player.getTeam() != null ? player.getTeam().getNome() : null;
    }

    private void linkMatchdays(OfficialSeries series, List<Long> matchdayIds) {
        for (Long matchdayId : matchdayIds) {
            if (matchdaySeriesRepository.existsByMatchdayIdAndSeriesId(matchdayId, series.getId())) continue;
            var matchday = matchdayRepository.findById(matchdayId)
                    .orElseThrow(() -> new ResourceNotFoundException("Giornata non trovata con id: " + matchdayId));
            matchdaySeriesRepository.save(MatchdaySeries.builder().matchday(matchday).series(series).build());
        }
    }

    private static PlayerGameStatAudit audit(PlayerGameStat stat, String action, StatSource source, String actor) {
        String snapshot = "oracle=" + candidate(stat.getOracleKills(), stat.getOracleDeaths(),
                stat.getOracleAssists(), stat.getOracleCs(), stat.getOracleWin())
                + ";manual=" + candidate(stat.getManualKills(), stat.getManualDeaths(),
                stat.getManualAssists(), stat.getManualCs(), stat.getManualWin())
                + ";effective=" + stat.getEffectiveSource() + ";conflict=" + stat.isConflict();
        return PlayerGameStatAudit.builder().stat(stat).action(action).source(source)
                .actor(actor).valuesSnapshot(snapshot).build();
    }

    private static String candidate(Integer kills, Integer deaths, Integer assists, Integer cs, Boolean win) {
        return kills == null ? "-" : kills + ":" + deaths + ":" + assists + ":" + cs + ":" + win;
    }
}
