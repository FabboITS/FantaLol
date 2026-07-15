package com.fantalol.backend.league;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface FantaTeamRepository extends JpaRepository<FantaTeam, Long> {

    List<FantaTeam> findByLeagueId(Long leagueId);

    List<FantaTeam> findByOwnerUsername(String username);

    Optional<FantaTeam> findByLeagueIdAndOwnerUsername(Long leagueId, String username);

    boolean existsByLeagueIdAndOwnerId(Long leagueId, Long ownerId);
}
