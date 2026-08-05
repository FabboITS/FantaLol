package com.fantalol.backend.lineup;

import com.fantalol.backend.team.PlayerRole;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface EffectiveLineupPeriodRepository extends JpaRepository<EffectiveLineupPeriod, Long> {

    List<EffectiveLineupPeriod> findByFantaTeamIdAndEffectiveUntilIsNull(Long fantaTeamId);

    @Query("""
            select period from EffectiveLineupPeriod period
            join fetch period.fantaTeam
            join fetch period.lecPlayer
            where period.fantaTeam.id in :fantaTeamIds
            order by period.fantaTeam.id, period.effectiveFrom
            """)
    List<EffectiveLineupPeriod> findByFantaTeamIdIn(
            @Param("fantaTeamIds") Collection<Long> fantaTeamIds);

    boolean existsByFantaTeamId(Long fantaTeamId);

    boolean existsByFantaTeamIdAndEffectiveFrom(Long fantaTeamId, Instant effectiveFrom);

    @Query("""
            select period from EffectiveLineupPeriod period
            where period.fantaTeam.id = :fantaTeamId
              and period.role = :role
              and period.effectiveFrom <= :playedAt
              and (period.effectiveUntil is null or period.effectiveUntil > :playedAt)
            """)
    Optional<EffectiveLineupPeriod> findActiveByFantaTeamIdAndRole(
            @Param("fantaTeamId") Long fantaTeamId,
            @Param("role") PlayerRole role,
            @Param("playedAt") Instant playedAt);

    @Query("""
            select period from EffectiveLineupPeriod period
            where period.fantaTeam.id = :fantaTeamId
              and period.effectiveFrom <= :playedAt
              and (period.effectiveUntil is null or period.effectiveUntil > :playedAt)
            """)
    List<EffectiveLineupPeriod> findActiveByFantaTeamId(
            @Param("fantaTeamId") Long fantaTeamId,
            @Param("playedAt") Instant playedAt);
}
