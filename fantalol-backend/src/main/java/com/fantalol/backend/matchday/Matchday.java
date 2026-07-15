package com.fantalol.backend.matchday;

import com.fantalol.backend.league.League;
import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Rappresenta una giornata di campionato LEC (es. "Spring Split - Week 3").
 * Relazione OneToMany verso {@link PlayerStat}: le statistiche di ciascun player per la giornata.
 */
@Entity
@Table(name = "matchdays", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"league_id", "numero"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Matchday {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotNull
    @Column(nullable = false)
    private Integer numero;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "league_id", nullable = false)
    private League league;

    @Column(length = 100)
    private String descrizione;

    private LocalDate data;

    @Column(nullable = false)
    @Builder.Default
    private boolean chiusa = false;

    @OneToMany(mappedBy = "matchday", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @Builder.Default
    private List<PlayerStat> statistiche = new ArrayList<>();
}
