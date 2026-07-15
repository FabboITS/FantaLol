package com.fantalol.backend.team;

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
 * Rappresenta una delle 10 organizzazioni che competono nella LEC
 * (League of Legends EMEA Championship).
 * <p>
 * Relazione OneToMany verso {@link LecPlayer}: un team ha più player in rosa.
 */
@Entity
@Table(name = "lec_teams")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LecTeam {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false, unique = true, length = 80)
    private String nome;

    @Column(length = 10)
    private String sigla;

    @Column(length = 255)
    private String logoUrl;

    @OneToMany(mappedBy = "team", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @Builder.Default
    private List<LecPlayer> giocatori = new ArrayList<>();
}
