package com.fantalol.backend.matchday;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.League;
import com.fantalol.backend.league.LeagueService;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class MatchdayScoringServiceTest {
    @Mock MatchdayRepository matchdayRepository;
    @Mock PlayerStatRepository playerStatRepository;
    @Mock com.fantalol.backend.team.LecPlayerRepository lecPlayerRepository;
    @Mock FantaScoreCalculator fantaScoreCalculator;
    @Mock FormationRepository formationRepository;
    @Mock FormationService formationService;
    @Mock FantaTeamRepository fantaTeamRepository;
    @Mock LeagueService leagueService;
    @Mock UserService userService;
    @InjectMocks MatchdayService service;

    @Test
    void averagesFivePlayersAndTreatsMissingStatsAsZero() {
        User creator = User.builder().username("creator").build();
        League league = League.builder().id(1L).admin(creator).auctionOpen(false).participantCount(5).build();
        FantaTeam team = FantaTeam.builder().id(1L).league(league).owner(creator).build();
        Matchday day = Matchday.builder().id(1L).numero(1).league(league).build();
        List<LecPlayer> players = java.util.stream.LongStream.rangeClosed(1, 5)
                .mapToObj(id -> LecPlayer.builder().id(id).nickname("P" + id).build()).toList();
        Formation formation = Formation.builder().fantaTeam(team).matchday(day)
                .source(FormationSource.SUBMITTED).titolari(Set.copyOf(players)).build();
        when(matchdayRepository.findById(1L)).thenReturn(Optional.of(day));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(creator);
        when(fantaTeamRepository.findByLeagueId(1L)).thenReturn(List.of(team));
        when(formationService.resolveEffectiveFormation(team, day)).thenReturn(formation);
        double[] scores = {10, 8, 6, 4};
        for (int i = 0; i < scores.length; i++) {
            PlayerStat stat = PlayerStat.builder().fantavoto(scores[i]).build();
            when(playerStatRepository.findByMatchdayIdAndLecPlayerId(1L, players.get(i).getId()))
                    .thenReturn(Optional.of(stat));
        }
        when(playerStatRepository.findByMatchdayIdAndLecPlayerId(1L, players.get(4).getId()))
                .thenReturn(Optional.empty());
        when(formationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(matchdayRepository.save(any(Matchday.class))).thenAnswer(inv -> inv.getArgument(0));

        service.chiudiGiornata("creator", 1L);

        assertThat(formation.getPunteggioTotale()).isEqualTo(5.6);
        assertThat(day.isChiusa()).isTrue();
    }

    @Test
    void missingFirstFormationScoresZero() {
        User creator = User.builder().username("creator").build();
        League league = League.builder().id(1L).admin(creator).auctionOpen(false).participantCount(5).build();
        FantaTeam team = FantaTeam.builder().id(1L).league(league).owner(creator).build();
        Matchday day = Matchday.builder().id(1L).numero(1).league(league).build();
        Formation missing = Formation.builder().fantaTeam(team).matchday(day)
                .source(FormationSource.MISSING).build();
        when(matchdayRepository.findById(1L)).thenReturn(Optional.of(day));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(creator);
        when(fantaTeamRepository.findByLeagueId(1L)).thenReturn(List.of(team));
        when(formationService.resolveEffectiveFormation(team, day)).thenReturn(missing);
        when(formationRepository.saveAll(any())).thenAnswer(inv -> inv.getArgument(0));
        when(matchdayRepository.save(any(Matchday.class))).thenAnswer(inv -> inv.getArgument(0));

        service.chiudiGiornata("creator", 1L);

        assertThat(missing.getPunteggioTotale()).isZero();
    }
}
