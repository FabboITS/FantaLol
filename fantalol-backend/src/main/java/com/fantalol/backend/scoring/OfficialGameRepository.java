package com.fantalol.backend.scoring;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface OfficialGameRepository extends JpaRepository<OfficialGame, Long> {
    Optional<OfficialGame> findByProviderAndExternalId(String provider, String externalId);
    List<OfficialGame> findBySeriesIdOrderByGameNumber(Long seriesId);
}
