package com.fantalol.backend.integration.oracle;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ProviderPlayerGameStatRepository extends JpaRepository<ProviderPlayerGameStat, Long> {
    List<ProviderPlayerGameStat> findByProviderGameId(Long providerGameId);

    List<ProviderPlayerGameStat> findAllByOrderByProviderGamePlayedAtAsc();

    Optional<ProviderPlayerGameStat> findByProviderGameExternalGameIdAndLecPlayerId(
            String externalGameId,
            Long playerId
    );
}
