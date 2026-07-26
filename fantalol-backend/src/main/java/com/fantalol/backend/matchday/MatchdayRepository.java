package com.fantalol.backend.matchday;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.time.LocalDate;

public interface MatchdayRepository extends JpaRepository<Matchday, Long> {
    Optional<Matchday> findByLeagueIdAndNumero(Long leagueId, Integer numero);
    boolean existsByLeagueIdAndChiusaFalse(Long leagueId);
    boolean existsByLeagueIdAndStatus(Long leagueId, MatchdayStatus status);
    Optional<Matchday> findByLeagueIdAndData(Long leagueId, LocalDate data);
}
