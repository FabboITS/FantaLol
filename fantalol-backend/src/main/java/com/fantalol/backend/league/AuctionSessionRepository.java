package com.fantalol.backend.league;

import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import java.time.Instant;
import java.util.*;

public interface AuctionSessionRepository extends JpaRepository<AuctionSession, Long> {
    Optional<AuctionSession> findFirstByLeagueIdAndStatus(Long leagueId, AuctionStatus status);
    List<AuctionSession> findByStatusAndEndsAtLessThanEqual(AuctionStatus status, Instant instant);
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from AuctionSession a where a.id = :id")
    Optional<AuctionSession> findByIdForUpdate(@Param("id") Long id);
}
