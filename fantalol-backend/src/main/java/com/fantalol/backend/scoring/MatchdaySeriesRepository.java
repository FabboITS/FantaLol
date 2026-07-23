package com.fantalol.backend.scoring;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MatchdaySeriesRepository extends JpaRepository<MatchdaySeries, Long> {
    List<MatchdaySeries> findByMatchdayId(Long matchdayId);
    List<MatchdaySeries> findBySeriesId(Long seriesId);
    boolean existsByMatchdayIdAndSeriesId(Long matchdayId, Long seriesId);
}
