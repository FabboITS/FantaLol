package com.fantalol.backend.integration.oracle;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
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
@Table(name = "provider_games", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"provider", "external_game_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProviderGame {
    public static final String ORACLES_ELIXIR = "ORACLES_ELIXIR";

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Builder.Default
    @Column(nullable = false, length = 30)
    private String provider = ORACLES_ELIXIR;

    @Column(name = "external_game_id", nullable = false, length = 160)
    private String externalGameId;

    @Column(name = "played_at", nullable = false)
    private Instant playedAt;

    @Column(nullable = false, length = 40)
    private String league;

    @Column(nullable = false, length = 40)
    private String split;

    @Column(name = "source_fingerprint", nullable = false, length = 64)
    private String sourceFingerprint;

    @Column(name = "source_first_seen_at", nullable = false)
    private Instant sourceFirstSeenAt;

    @Column(name = "source_last_seen_at", nullable = false)
    private Instant sourceLastSeenAt;

    @PrePersist
    void initializeSourceTimestamps() {
        Instant now = Instant.now();
        if (sourceFirstSeenAt == null) {
            sourceFirstSeenAt = now;
        }
        if (sourceLastSeenAt == null) {
            sourceLastSeenAt = now;
        }
    }

}
