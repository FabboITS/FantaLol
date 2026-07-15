package com.fantalol.backend.league.dto;

import com.fantalol.backend.league.AuctionSession;
import java.time.Instant;

public record AuctionResponse(Long id, Long leagueId, Long lecPlayerId, String playerNickname,
                              String playerRole, Integer currentBid, Long highestBidderId,
                              String highestBidderName, Instant endsAt, String status) {
    public static AuctionResponse from(AuctionSession a) {
        return new AuctionResponse(a.getId(), a.getLeague().getId(), a.getPlayer().getId(),
                a.getPlayer().getNickname(), a.getPlayer().getRuolo().name(), a.getCurrentBid(),
                a.getHighestBidder() == null ? null : a.getHighestBidder().getId(),
                a.getHighestBidder() == null ? null : a.getHighestBidder().getNome(),
                a.getEndsAt(), a.getStatus().name());
    }
}
