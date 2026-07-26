package com.fantalol.backend.scoring;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PlayerGameStatRepository extends JpaRepository<PlayerGameStat, Long> {
    Optional<PlayerGameStat> findByGameIdAndPlayerId(Long gameId, Long playerId);
    List<PlayerGameStat> findByGameSeriesIdAndPlayerId(Long seriesId, Long playerId);
    List<PlayerGameStat> findByGameSeriesId(Long seriesId);
    List<PlayerGameStat> findByConflictTrueOrderByGamePlayedAtDesc();
    long countByGameSeriesId(Long seriesId);
    long countByGameSeriesIdAndConflictTrue(Long seriesId);
    long countByGameIdAndEffectiveSourceIsNotNull(Long gameId);
}
