package com.fantalol.backend.matchday;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface FormationRepository extends JpaRepository<Formation, Long> {

    Optional<Formation> findByFantaTeamIdAndMatchdayId(Long fantaTeamId, Long matchdayId);

    List<Formation> findByMatchdayId(Long matchdayId);

    List<Formation> findByFantaTeamId(Long fantaTeamId);

    Optional<Formation> findFirstByFantaTeamIdOrderByMatchdayNumeroDesc(Long fantaTeamId);

    Optional<Formation> findFirstByFantaTeamIdAndMatchdayNumeroLessThanAndSourceOrderByMatchdayNumeroDesc(
            Long fantaTeamId, Integer matchdayNumero, FormationSource source);
}
