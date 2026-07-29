package com.fantalol.backend.integration.lec;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ProviderSyncStateRepository extends JpaRepository<ProviderSyncState, Long> {
    Optional<ProviderSyncState> findByProvider(String provider);
}
