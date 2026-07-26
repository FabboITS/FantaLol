package com.fantalol.backend.scoring;

import com.fantalol.backend.matchday.Matchday;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "matchday_series", uniqueConstraints = @UniqueConstraint(columnNames = {"matchday_id", "series_id"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MatchdaySeries {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "matchday_id", nullable = false)
    private Matchday matchday;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "series_id", nullable = false)
    private OfficialSeries series;
}
