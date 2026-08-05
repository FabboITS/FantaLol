package com.fantalol.backend.matchday;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.team.LecPlayer;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.HashSet;
import java.util.Set;

/**
 * Formazione schierata da una {@link FantaTeam} per una specifica {@link Matchday}.
 * <p>
 * Relazione ManyToOne verso {@link FantaTeam} e {@link Matchday}.
 * Relazione ManyToMany (semplice, tramite tabella di join) verso {@link LecPlayer}:
 * l'insieme dei titolari schierati per la giornata.
 */
@Entity
@Table(name = "formations", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"fanta_team_id", "matchday_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Formation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "fanta_team_id", nullable = false)
    private FantaTeam fantaTeam;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "matchday_id", nullable = false)
    private Matchday matchday;

    /** Relazione ManyToMany: i player titolari schierati in questa formazione. */
    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "formation_titolari",
            joinColumns = @JoinColumn(name = "formation_id"),
            inverseJoinColumns = @JoinColumn(name = "lec_player_id")
    )
    @Builder.Default
    private Set<LecPlayer> titolari = new HashSet<>();

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private FormationSource source = FormationSource.SUBMITTED;

    @Column(nullable = false)
    @Builder.Default
    private boolean confirmed = false;

    /** Punteggio totale della formazione per la giornata, calcolato a chiusura giornata. */
    private Double punteggioTotale;
}
