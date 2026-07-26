package com.fantalol.backend.scoring;

import org.springframework.data.jpa.repository.JpaRepository;

public interface PlayerGameStatAuditRepository extends JpaRepository<PlayerGameStatAudit, Long> {
}
