package com.fantalol.backend.league;

import com.fantalol.backend.team.LecPlayer;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

/**
 * Classe associativa che rappresenta l'acquisto (asta) di un {@link LecPlayer}
 * da parte di una {@link FantaTeam}: implementa la relazione ManyToMany
 * FantaTeam &lt;-&gt; LecPlayer arricchendola con attributi propri
 * (crediti spesi, data di acquisto), secondo la best practice JPA per
 * le relazioni molti-a-molti con payload aggiuntivo.
 */
@Entity
@Table(name = "roster_entries", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"fanta_team_id", "lec_player_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RosterEntry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "fanta_team_id", nullable = false)
    private FantaTeam fantaTeam;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "lec_player_id", nullable = false)
    private LecPlayer lecPlayer;

    @Column(nullable = false)
    private Integer creditiSpesi;

    @Column(nullable = false)
    private Instant dataAcquisto;

    @PrePersist
    void prePersist() {
        if (dataAcquisto == null) {
            dataAcquisto = Instant.now();
        }
    }
}
