package com.fantalol.backend.user;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Profilo esteso dell'utente (dati facoltativi di personalizzazione).
 * Relazione OneToOne "owning side" verso {@link User} tramite chiave esterna dedicata.
 */
@Entity
@Table(name = "user_profiles")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(length = 60)
    private String nomeVisualizzato;

    @Column(length = 255)
    private String bio;

    @Column(length = 255)
    private String avatarUrl;

    @Column(length = 60)
    private String summonerName;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false, unique = true)
    private User user;
}
