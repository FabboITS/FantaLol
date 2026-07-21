package com.fantalol.backend.team;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Giocatore professionista che compete nella LEC per uno dei 10 team ammessi.
 * <p>
 * Relazione ManyToOne verso {@link LecTeam}: ogni player appartiene a un solo team.
 */
@Entity
@Table(name = "lec_players")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LecPlayer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false, length = 60)
    private String nickname;

    @Column(length = 120)
    private String nomeReale;

    @Column(length = 60)
    private String nazionalita;

    @Column(length = 255)
    private String imageUrl;

    @Column(name = "oracle_player_id", unique = true, length = 120)
    private String oraclePlayerId;

    @NotNull
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PlayerRole ruolo;

    /** Quotazione iniziale in crediti fantacalcistici, usata come base d'asta. */
    @NotNull
    @Positive
    @Column(nullable = false)
    private Integer quotazione;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "team_id", nullable = false)
    private LecTeam team;
}
