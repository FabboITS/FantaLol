package com.fantalol.backend.matchday;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ImportedGameRepository extends JpaRepository<ImportedGame, Long> {
    boolean existsByProviderAndExternalGameId(String provider, String externalGameId);
}
