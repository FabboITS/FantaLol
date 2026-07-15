package com.fantalol.backend.league;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import jakarta.persistence.LockModeType;

import java.util.Optional;

public interface LeagueRepository extends JpaRepository<League, Long> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select l from League l where l.id = :id")
    Optional<League> findByIdForUpdate(@Param("id") Long id);
    Optional<League> findByCodiceInvito(String codiceInvito);
}
