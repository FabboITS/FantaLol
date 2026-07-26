package com.fantalol.backend.scoring;

import org.springframework.data.jpa.repository.JpaRepository;

public interface MatchdayLockAuditRepository extends JpaRepository<MatchdayLockAudit, Long> {
}
