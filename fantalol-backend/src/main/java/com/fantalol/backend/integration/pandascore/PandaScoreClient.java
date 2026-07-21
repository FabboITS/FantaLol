package com.fantalol.backend.integration.pandascore;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@RequiredArgsConstructor
public class PandaScoreClient {
    private final RestClient pandaScoreRestClient;

    public JsonNode getTournamentMatches(long tournamentId) {
        return pandaScoreRestClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/lol/matches")
                        .queryParam("filter[tournament_id]", tournamentId)
                        .queryParam("sort", "begin_at")
                        .queryParam("per_page", 100)
                        .build())
                .retrieve()
                .body(JsonNode.class);
    }

    public JsonNode getMatch(long matchId) {
        return pandaScoreRestClient.get()
                .uri("/lol/matches/{matchId}", matchId)
                .retrieve()
                .body(JsonNode.class);
    }
}
