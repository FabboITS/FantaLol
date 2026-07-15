package com.fantalol.backend.matchday;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface MatchdayRepository extends JpaRepository<Matchday, Long> {
    Optional<Matchday> findByLeagueIdAndNumero(Long leagueId, Integer numero);
}
