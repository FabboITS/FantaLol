package com.fantalol.backend.league;

import com.fantalol.backend.user.User;
import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.ArrayList;
import java.util.List;

/**
 * Squadra fantacalcistica posseduta da un {@link User} all'interno di una {@link League}.
 * <p>
 * Relazione ManyToOne verso {@link League} e verso {@link User} (owner).
 * Relazione ManyToMany (tramite classe associativa {@link RosterEntry}) verso i player LEC
 * acquistati all'asta: rappresenta la rosa della squadra.
 */
@Entity
@Table(name = "fanta_teams", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"league_id", "owner_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FantaTeam {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false, length = 80)
    private String nome;

    @Column(nullable = false)
    private Integer creditiResidui;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "league_id", nullable = false)
    private League league;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "owner_id", nullable = false)
    private User owner;

    @Column(nullable = false)
    @Builder.Default
    private Double punti = 0.0;

    /** Rosa della squadra: relazione ManyToMany implementata tramite classe associativa (crediti spesi, data acquisto). */
    @OneToMany(mappedBy = "fantaTeam", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @Builder.Default
    private List<RosterEntry> rosa = new ArrayList<>();
}
