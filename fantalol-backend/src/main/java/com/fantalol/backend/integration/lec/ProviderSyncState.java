package com.fantalol.backend.integration.lec;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

@Entity
@Table(name = "provider_sync_states", uniqueConstraints = {
        @UniqueConstraint(columnNames = "provider")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProviderSyncState {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 40)
    private String provider;

    @Column(nullable = false, length = 20)
    private String status;

    @Column(name = "last_attempt_at", nullable = false)
    private Instant lastAttemptAt;

    @Column(name = "last_success_at")
    private Instant lastSuccessAt;

    @Column(name = "last_error", length = 1000)
    private String lastError;

    @Lob
    @Column(name = "provider_snapshot")
    private String providerSnapshot;

    @Column(name = "inserted_games", nullable = false)
    private int insertedGames;

    @Column(name = "updated_games", nullable = false)
    private int updatedGames;

    @Column(name = "skipped_games", nullable = false)
    private int skippedGames;

    @Column(name = "failed_games", nullable = false)
    private int failedGames;

    @Lob
    @Column(name = "unmatched_players")
    private String unmatchedPlayers;
}
