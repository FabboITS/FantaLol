package com.fantalol.backend.matchday;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.scoring.ScoringFormulaVersion;
import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Statistiche reali di un {@link LecPlayer} in una determinata {@link Matchday},
 * inserite manualmente dall'amministratore dopo lo svolgimento delle partite reali.
 * Da questi dati viene calcolato il "fantavoto" (vedi {@code FantaScoreCalculator}).
 * <p>
 * Relazioni ManyToOne verso {@link Matchday} e {@link LecPlayer}.
 */
@Entity
@Table(name = "player_stats", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"matchday_id", "lec_player_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PlayerStat {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "matchday_id", nullable = false)
    private Matchday matchday;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "lec_player_id", nullable = false)
    private LecPlayer lecPlayer;

    @Min(0)
    @Column(nullable = false)
    @Builder.Default
    private Integer kills = 0;

    @Min(0)
    @Column(nullable = false)
    @Builder.Default
    private Integer morti = 0;

    @Min(0)
    @Column(nullable = false)
    @Builder.Default
    private Integer assist = 0;

    @Min(0)
    @Column(nullable = false)
    @Builder.Default
    private Integer cs = 0;

    @Column(nullable = false)
    @Builder.Default
    private boolean vittoria = false;

    @Min(0)
    @Column(nullable = false)
    @Builder.Default
    private Integer wins = 0;

    @Min(0)
    @Column(nullable = false)
    @Builder.Default
    private Integer gamesPlayed = 1;

    @Enumerated(EnumType.STRING)
    @Column(length = 40)
    @Builder.Default
    private ScoringFormulaVersion formulaVersion = ScoringFormulaVersion.SUMMER_2026_V1;

    @PostLoad
    void initializeWinsForLegacyRows() {
        if (wins == null) {
            wins = vittoria ? 1 : 0;
        }
        if (gamesPlayed == null || gamesPlayed < 1) {
            gamesPlayed = 1;
        }
        if (formulaVersion == null) {
            formulaVersion = ScoringFormulaVersion.HISTORICAL;
        }
    }

    /** Fantasy score calculated from the weekly aggregate statistics. */
    @Column(nullable = false)
    private Double fantavoto;
}
