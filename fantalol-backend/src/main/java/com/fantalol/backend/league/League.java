package com.fantalol.backend.league;

import com.fantalol.backend.user.User;
import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Lega privata di Fanta LoL: un gruppo di utenti che competono tra loro
 * con le rose costruite tramite asta a crediti.
 * <p>
 * Relazione ManyToOne verso {@link User} (il creatore/admin della lega).
 * Relazione OneToMany verso {@link FantaTeam} (le squadre iscritte alla lega).
 */
@Entity
@Table(name = "leagues")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class League {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false, length = 100)
    private String nome;

    @Column(nullable = false, unique = true, length = 12)
    private String codiceInvito;

    @NotNull
    @Column(nullable = false)
    private Integer creditiIniziali;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "admin_id", nullable = false)
    private User admin;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false)
    @Builder.Default
    private boolean auctionOpen = false;

    @OneToMany(mappedBy = "league", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @Builder.Default
    private List<FantaTeam> fantaTeams = new ArrayList<>();

    @OneToMany(mappedBy = "league", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @Builder.Default
    private List<AuctionSession> auctions = new ArrayList<>();

    @PrePersist
    void prePersist() {
        if (createdAt == null) {
            createdAt = Instant.now();
        }
        if (codiceInvito == null) {
            codiceInvito = UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        }
    }
}
