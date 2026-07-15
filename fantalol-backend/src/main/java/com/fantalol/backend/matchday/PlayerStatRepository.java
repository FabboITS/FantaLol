package com.fantalol.backend.matchday;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PlayerStatRepository extends JpaRepository<PlayerStat, Long> {

    List<PlayerStat> findByMatchdayId(Long matchdayId);

    Optional<PlayerStat> findByMatchdayIdAndLecPlayerId(Long matchdayId, Long lecPlayerId);
}
