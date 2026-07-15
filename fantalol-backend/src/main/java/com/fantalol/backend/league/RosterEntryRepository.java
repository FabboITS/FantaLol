package com.fantalol.backend.league;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface RosterEntryRepository extends JpaRepository<RosterEntry, Long> {

    List<RosterEntry> findByFantaTeamId(Long fantaTeamId);

    Optional<RosterEntry> findByFantaTeamIdAndLecPlayerId(Long fantaTeamId, Long lecPlayerId);

    boolean existsByFantaTeamIdAndLecPlayerId(Long fantaTeamId, Long lecPlayerId);

    /** Verifica se un player LEC è già stato acquistato da un'altra squadra nella stessa lega. */
    boolean existsByFantaTeam_League_IdAndLecPlayerId(Long leagueId, Long lecPlayerId);
}
