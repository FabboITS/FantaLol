package com.fantalol.backend.league;

import com.fantalol.backend.league.dto.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auctions")
@RequiredArgsConstructor
public class AuctionController {
    private final AuctionService auctionService;

    @GetMapping("/active")
    public AuctionResponse active(@RequestParam Long leagueId) { return auctionService.active(leagueId); }

    @PostMapping
    public ResponseEntity<AuctionResponse> start(Authentication auth, @Valid @RequestBody AuctionStartRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(auctionService.start(auth.getName(), request));
    }

    @PostMapping("/{id}/bids")
    public AuctionResponse bid(Authentication auth, @PathVariable Long id, @Valid @RequestBody AuctionBidRequest request) {
        return auctionService.bid(auth.getName(), id, request);
    }
}
