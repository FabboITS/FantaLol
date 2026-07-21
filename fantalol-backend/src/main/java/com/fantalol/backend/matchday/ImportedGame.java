package com.fantalol.backend.matchday;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "imported_games", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"provider", "external_game_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ImportedGame {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 30)
    private String provider;

    @Column(name = "external_game_id", nullable = false, length = 160)
    private String externalGameId;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "matchday_id", nullable = false)
    private Matchday matchday;
}
