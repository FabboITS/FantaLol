package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.integration.oracle.dto.ManualPlayerGameCorrectionRequest;
import com.fantalol.backend.scoring.GameScoreCalculator;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;

@Service
@RequiredArgsConstructor
public class PlayerGameCorrectionService {
    private final ProviderPlayerGameStatRepository repository;
    private final GameScoreCalculator scoreCalculator;
    private final Clock clock;

    @Transactional
    public ProviderPlayerGameStat correct(
            String gameId,
            Long playerId,
            ManualPlayerGameCorrectionRequest request,
            String actor
    ) {
        ProviderPlayerGameStat stat = find(gameId, playerId);
        stat.setCorrectedParticipated(value(request.participated(), stat.isRawParticipated()));
        stat.setCorrectedKills(value(request.kills(), stat.getRawKills()));
        stat.setCorrectedDeaths(value(request.deaths(), stat.getRawDeaths()));
        stat.setCorrectedAssists(value(request.assists(), stat.getRawAssists()));
        stat.setCorrectedCs(value(request.cs(), stat.getRawCs()));
        stat.setCorrectedVisionScore(value(request.visionScore(), stat.getRawVisionScore()));
        stat.setCorrectedWin(value(request.win(), stat.isRawWin()));
        stat.setFantasyScore(score(
                stat,
                stat.getCorrectedKills(),
                stat.getCorrectedDeaths(),
                stat.getCorrectedAssists(),
                stat.getCorrectedCs(),
                stat.getCorrectedVisionScore(),
                stat.getCorrectedWin()));
        stat.setOverridden(true);
        stat.setOverrideActor(actor);
        stat.setOverriddenAt(clock.instant());
        return repository.save(stat);
    }

    @Transactional
    public ProviderPlayerGameStat restore(String gameId, Long playerId) {
        ProviderPlayerGameStat stat = find(gameId, playerId);
        stat.setCorrectedParticipated(null);
        stat.setCorrectedKills(null);
        stat.setCorrectedDeaths(null);
        stat.setCorrectedAssists(null);
        stat.setCorrectedCs(null);
        stat.setCorrectedVisionScore(null);
        stat.setCorrectedWin(null);
        stat.setOverridden(false);
        stat.setOverrideActor(null);
        stat.setOverriddenAt(null);
        stat.setFantasyScore(score(
                stat,
                stat.getRawKills(),
                stat.getRawDeaths(),
                stat.getRawAssists(),
                stat.getRawCs(),
                stat.getRawVisionScore(),
                stat.isRawWin()));
        return repository.save(stat);
    }

    private ProviderPlayerGameStat find(String gameId, Long playerId) {
        return repository.findByProviderGameExternalGameIdAndLecPlayerId(gameId, playerId)
                .orElseThrow(() -> new ResourceNotFoundException(
                        "LEC player-game not found: " + gameId + "/" + playerId));
    }

    private double score(
            ProviderPlayerGameStat stat,
            int kills,
            int deaths,
            int assists,
            int cs,
            int visionScore,
            boolean win
    ) {
        return scoreCalculator.calculate(
                stat.getSourceRole(),
                kills,
                deaths,
                assists,
                cs,
                visionScore,
                win);
    }

    private static <T> T value(T corrected, T provider) {
        return corrected == null ? provider : corrected;
    }
}
