package com.fantalol.backend.scoring;

import com.fantalol.backend.league.FantaTeamService;
import com.fantalol.backend.league.LeagueService;
import com.fantalol.backend.scoring.dto.CumulativeFantasyTeamScore;
import com.fantalol.backend.scoring.dto.CumulativePlayerScore;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class CumulativeScoringController {

    private final CumulativeScoringService cumulativeScoringService;
    private final FantaTeamService fantaTeamService;
    private final LeagueService leagueService;

    @GetMapping("/api/lec/cumulative-performances")
    public List<CumulativePlayerScore> playerScores() {
        return cumulativeScoringService.playerScores();
    }

    @GetMapping("/api/fanta-teams/{id}/cumulative-score")
    public CumulativeFantasyTeamScore teamScore(Authentication authentication, @PathVariable Long id) {
        return fantaTeamService.cumulativeScore(authentication.getName(), id);
    }

    @GetMapping("/api/leagues/{id}/cumulative-ranking")
    public List<CumulativeFantasyTeamScore> leagueRanking(Authentication authentication, @PathVariable Long id) {
        leagueService.findById(authentication.getName(), id);
        return cumulativeScoringService.leagueRanking(id);
    }
}
