package com.fantalol.backend.scoring;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface OfficialSeriesRepository extends JpaRepository<OfficialSeries, Long> {
    Optional<OfficialSeries> findByProviderAndExternalId(String provider, String externalId);
}
