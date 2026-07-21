package com.fantalol.backend.integration.pandascore;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/pandascore")
@RequiredArgsConstructor
public class PandaScoreAdminController {
    private final PandaScoreClient client;

    @GetMapping("/tournaments/{tournamentId}/matches")
    public JsonNode tournamentMatches(@PathVariable long tournamentId) {
        return client.getTournamentMatches(tournamentId);
    }

    @GetMapping("/matches/{matchId}")
    public JsonNode match(@PathVariable long matchId) {
        return client.getMatch(matchId);
    }
}
