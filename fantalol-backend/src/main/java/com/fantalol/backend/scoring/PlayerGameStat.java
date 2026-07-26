package com.fantalol.backend.scoring;

import com.fantalol.backend.team.LecPlayer;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.Objects;

@Entity
@Table(name = "player_game_stats", uniqueConstraints = @UniqueConstraint(columnNames = {"game_id", "lec_player_id"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PlayerGameStat {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "game_id", nullable = false)
    private OfficialGame game;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "lec_player_id", nullable = false)
    private LecPlayer player;

    /** Team name captured when this game was imported, so later roster changes do not rewrite history. */
    @Column(name = "team_name_snapshot", length = 100)
    private String teamNameSnapshot;

    private Integer oracleKills;
    private Integer oracleDeaths;
    private Integer oracleAssists;
    private Integer oracleCs;
    private Boolean oracleWin;
    private Instant oracleUpdatedAt;

    private Integer manualKills;
    private Integer manualDeaths;
    private Integer manualAssists;
    private Integer manualCs;
    private Boolean manualWin;
    private Instant manualUpdatedAt;
    private String manualUpdatedBy;

    @Enumerated(EnumType.STRING)
    @Column(length = 20)
    private StatSource effectiveSource;

    @Column(nullable = false)
    @Builder.Default
    private boolean conflict = false;

    @Column(length = 300)
    private String resolvedPairFingerprint;

    public void submit(StatSource source, int kills, int deaths, int assists, int cs, boolean win, String actor) {
        if (source == StatSource.ORACLE) {
            oracleKills = kills;
            oracleDeaths = deaths;
            oracleAssists = assists;
            oracleCs = cs;
            oracleWin = win;
            oracleUpdatedAt = Instant.now();
        } else {
            manualKills = kills;
            manualDeaths = deaths;
            manualAssists = assists;
            manualCs = cs;
            manualWin = win;
            manualUpdatedAt = Instant.now();
            manualUpdatedBy = actor;
        }
        refreshConflictState(source);
    }

    public void resolve(StatSource source) {
        if (!has(source)) {
            throw new IllegalStateException("No " + source + " candidate exists");
        }
        effectiveSource = source;
        conflict = false;
        resolvedPairFingerprint = pairFingerprint();
    }

    public boolean has(StatSource source) {
        return source == StatSource.ORACLE ? oracleKills != null : manualKills != null;
    }

    public int effectiveKills() { return effectiveSource == StatSource.ORACLE ? oracleKills : manualKills; }
    public int effectiveDeaths() { return effectiveSource == StatSource.ORACLE ? oracleDeaths : manualDeaths; }
    public int effectiveAssists() { return effectiveSource == StatSource.ORACLE ? oracleAssists : manualAssists; }
    public int effectiveCs() { return effectiveSource == StatSource.ORACLE ? oracleCs : manualCs; }
    public boolean effectiveWin() { return effectiveSource == StatSource.ORACLE ? oracleWin : manualWin; }

    private void refreshConflictState(StatSource submittedSource) {
        if (!has(StatSource.ORACLE) || !has(StatSource.MANUAL)) {
            effectiveSource = submittedSource;
            conflict = false;
            return;
        }
        if (sameCandidates()) {
            effectiveSource = StatSource.ORACLE;
            conflict = false;
            resolvedPairFingerprint = pairFingerprint();
            return;
        }
        if (Objects.equals(resolvedPairFingerprint, pairFingerprint())) {
            conflict = false;
            return;
        }
        if (effectiveSource == null) {
            effectiveSource = submittedSource == StatSource.ORACLE ? StatSource.MANUAL : StatSource.ORACLE;
        }
        conflict = true;
    }

    private boolean sameCandidates() {
        return Objects.equals(oracleKills, manualKills)
                && Objects.equals(oracleDeaths, manualDeaths)
                && Objects.equals(oracleAssists, manualAssists)
                && Objects.equals(oracleCs, manualCs)
                && Objects.equals(oracleWin, manualWin);
    }

    private String pairFingerprint() {
        return candidateFingerprint(StatSource.ORACLE) + "|" + candidateFingerprint(StatSource.MANUAL);
    }

    private String candidateFingerprint(StatSource source) {
        if (!has(source)) return "-";
        if (source == StatSource.ORACLE) {
            return oracleKills + ":" + oracleDeaths + ":" + oracleAssists + ":" + oracleCs + ":" + oracleWin;
        }
        return manualKills + ":" + manualDeaths + ":" + manualAssists + ":" + manualCs + ":" + manualWin;
    }
}
