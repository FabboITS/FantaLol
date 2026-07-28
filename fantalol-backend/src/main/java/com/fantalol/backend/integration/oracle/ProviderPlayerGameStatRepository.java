package com.fantalol.backend.integration.oracle;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface ProviderPlayerGameStatRepository extends JpaRepository<ProviderPlayerGameStat, Long> {
    List<ProviderPlayerGameStat> findByProviderGameId(Long providerGameId);

    @Query("""
            select stat from ProviderPlayerGameStat stat
            join fetch stat.providerGame game
            join fetch stat.lecPlayer player
            order by game.playedAt asc
            """)
    List<ProviderPlayerGameStat> findAllByOrderByProviderGamePlayedAtAsc();

    Optional<ProviderPlayerGameStat> findByProviderGameExternalGameIdAndLecPlayerId(
            String externalGameId,
            Long playerId
    );
}
