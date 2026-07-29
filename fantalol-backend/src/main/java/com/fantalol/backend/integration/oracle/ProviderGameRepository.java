package com.fantalol.backend.integration.oracle;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ProviderGameRepository extends JpaRepository<ProviderGame, Long> {
    Optional<ProviderGame> findByProviderAndExternalGameId(String provider, String externalGameId);
}
