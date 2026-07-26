package com.fantalol.backend.scoring;

import com.fantalol.backend.matchday.Matchday;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "matchday_lock_audits")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MatchdayLockAudit {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "matchday_id", nullable = false)
    private Matchday matchday;

    @Column(nullable = false)
    private boolean locked;

    @Column(nullable = false, length = 80)
    private String actor;

    @Column(nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();
}
