package com.fantalol.backend.team;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface LecTeamRepository extends JpaRepository<LecTeam, Long> {
    Optional<LecTeam> findByNomeIgnoreCase(String nome);

    boolean existsByNomeIgnoreCase(String nome);
}
