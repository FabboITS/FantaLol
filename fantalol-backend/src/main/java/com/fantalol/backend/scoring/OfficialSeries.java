package com.fantalol.backend.scoring;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Table(name = "official_series", uniqueConstraints = @UniqueConstraint(columnNames = {"provider", "external_id"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OfficialSeries {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 30)
    private String provider;

    @Column(name = "external_id", nullable = false, length = 180)
    private String externalId;

    @Column(length = 80)
    private String stage;

    @Column(name = "team_one", length = 100)
    private String teamOne;

    @Column(name = "team_two", length = 100)
    private String teamTwo;

    private Instant scheduledAt;

    @Column(nullable = false)
    @Builder.Default
    private boolean completed = false;
}
