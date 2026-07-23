package com.fantalol.backend.scoring;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "official_games", uniqueConstraints = @UniqueConstraint(columnNames = {"provider", "external_id"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OfficialGame {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "series_id", nullable = false)
    private OfficialSeries series;

    @Column(nullable = false, length = 30)
    private String provider;

    @Column(name = "external_id", nullable = false, length = 180)
    private String externalId;

    @Column(nullable = false)
    private Integer gameNumber;

    private Instant playedAt;
}
