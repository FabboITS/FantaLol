package com.fantalol.backend.league;

import com.fantalol.backend.team.LecPlayer;
import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "auction_sessions")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class AuctionSession {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "league_id", nullable = false)
    private League league;
    @ManyToOne(fetch = FetchType.LAZY, optional = false) @JoinColumn(name = "lec_player_id", nullable = false)
    private LecPlayer player;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "highest_bidder_id")
    private FantaTeam highestBidder;
    @Column(nullable = false) private Integer currentBid;
    @Column(nullable = false) private Instant endsAt;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 20)
    private AuctionStatus status;
}
