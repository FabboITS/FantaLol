package com.fantalol.backend.integration.oracle;

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
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;
import java.util.Objects;

@Entity
@Table(name = "provider_player_game_stats", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"provider_game_id", "lec_player_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProviderPlayerGameStat {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "provider_game_id", nullable = false)
    private ProviderGame providerGame;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "lec_player_id", nullable = false)
    private LecPlayer lecPlayer;

    @Column(name = "external_player_id", nullable = false, length = 120)
    private String externalPlayerId;

    @Column(name = "source_nickname", nullable = false, length = 120)
    private String sourceNickname;

    @Column(name = "source_team_name", nullable = false, length = 120)
    private String sourceTeamName;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_role", nullable = false, length = 20)
    private PlayerRole sourceRole;

    @Column(name = "source_champion", nullable = false, length = 80)
    private String sourceChampion;

    @Column(name = "source_fingerprint", nullable = false, length = 64)
    private String sourceFingerprint;

    @Column(name = "raw_participated", nullable = false)
    private boolean rawParticipated;

    @Column(name = "raw_kills", nullable = false)
    private int rawKills;

    @Column(name = "raw_deaths", nullable = false)
    private int rawDeaths;

    @Column(name = "raw_assists", nullable = false)
    private int rawAssists;

    @Column(name = "raw_cs", nullable = false)
    private int rawCs;

    @Column(name = "raw_vision_score", nullable = false)
    private int rawVisionScore;

    @Column(name = "raw_win", nullable = false)
    private boolean rawWin;

    @Column(name = "corrected_kills")
    private Integer correctedKills;

    @Column(name = "corrected_participated")
    private Boolean correctedParticipated;

    @Column(name = "corrected_deaths")
    private Integer correctedDeaths;

    @Column(name = "corrected_assists")
    private Integer correctedAssists;

    @Column(name = "corrected_cs")
    private Integer correctedCs;

    @Column(name = "corrected_vision_score")
    private Integer correctedVisionScore;

    @Column(name = "corrected_win")
    private Boolean correctedWin;

    @Column(name = "fantasy_score", nullable = false)
    private double fantasyScore;

    @Column(nullable = false)
    private boolean overridden;

    @Column(name = "override_actor", length = 120)
    private String overrideActor;

    @Column(name = "overridden_at")
    private Instant overriddenAt;

    public boolean isActiveSourceVersion() {
        return overridden || providerGame != null
                && Objects.equals(sourceFingerprint, providerGame.getSourceFingerprint());
    }
}
