package com.fantalol.backend.lineup;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

@Entity
@Table(name = "effective_lineup_periods",
        uniqueConstraints = @UniqueConstraint(columnNames = {"fanta_team_id", "role", "effective_from"}),
        indexes = @Index(name = "idx_lineup_period_active", columnList = "fanta_team_id,role,effective_from"))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class EffectiveLineupPeriod {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "fanta_team_id", nullable = false)
    private FantaTeam fantaTeam;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PlayerRole role;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "lec_player_id", nullable = false)
    private LecPlayer lecPlayer;

    @Column(name = "effective_from", nullable = false, updatable = false)
    private Instant effectiveFrom;

    @Column(name = "effective_until")
    private Instant effectiveUntil;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20, updatable = false)
    private LineupPeriodOrigin origin;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @PrePersist
    void prePersist() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }
}
