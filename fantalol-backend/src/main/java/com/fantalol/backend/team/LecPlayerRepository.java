package com.fantalol.backend.team;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import jakarta.persistence.LockModeType;

import java.util.List;
import java.util.Optional;

public interface LecPlayerRepository extends JpaRepository<LecPlayer, Long> {

    /** Serializza le offerte concorrenti sullo stesso player durante un acquisto. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select p from LecPlayer p where p.id = :id")
    Optional<LecPlayer> findByIdForUpdate(@Param("id") Long id);

    List<LecPlayer> findByTeamId(Long teamId);

    List<LecPlayer> findByRuolo(PlayerRole ruolo);
}
