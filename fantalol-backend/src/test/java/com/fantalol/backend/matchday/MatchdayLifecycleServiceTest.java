package com.fantalol.backend.matchday;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.league.League;
import com.fantalol.backend.league.LeagueService;
import com.fantalol.backend.matchday.dto.MatchdayRequest;
import com.fantalol.backend.matchday.dto.PlayerStatRequest;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class MatchdayLifecycleServiceTest {
    @Mock MatchdayRepository matchdayRepository;
    @Mock PlayerStatRepository playerStatRepository;
    @Mock com.fantalol.backend.team.LecPlayerRepository lecPlayerRepository;
    @Mock FantaScoreCalculator fantaScoreCalculator;
    @Mock FormationRepository formationRepository;
    @Mock LeagueService leagueService;
    @Mock UserService userService;
    @InjectMocks MatchdayService service;

    private League league;

    @BeforeEach
    void setUp() {
        User creator = User.builder().username("creator").role(com.fantalol.backend.user.Role.ADMIN).build();
        league = League.builder().id(1L).nome("LEC").admin(creator).auctionOpen(false).build();
    }

    @Test
    void creatingMatchdayStartsCompetitionAndOpensAuction() {
        when(leagueService.getOrThrow(1L)).thenReturn(league);
        when(userService.findByUsernameOrThrow("creator")).thenReturn(league.getAdmin());
        when(matchdayRepository.existsByLeagueIdAndChiusaFalse(1L)).thenReturn(false);
        when(matchdayRepository.findByLeagueIdAndNumero(1L, 1)).thenReturn(Optional.empty());
        when(matchdayRepository.save(any(Matchday.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(leagueService.startCompetitionAndOpenAuction(league)).thenAnswer(invocation -> {
            league.setAuctionOpen(true);
            return league;
        });

        var response = service.create("creator", new MatchdayRequest(1L, 1, "Week 1", null));

        assertThat(response.auctionLocked()).isTrue();
        verify(leagueService).startCompetitionAndOpenAuction(league);
    }

    @Test
    void rejectsSecondOpenMatchday() {
        when(leagueService.getOrThrow(1L)).thenReturn(league);
        when(userService.findByUsernameOrThrow("creator")).thenReturn(league.getAdmin());
        when(matchdayRepository.existsByLeagueIdAndChiusaFalse(1L)).thenReturn(true);

        assertThatThrownBy(() -> service.create("creator", new MatchdayRequest(1L, 2, null, null)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("giornata aperta");
    }

    @Test
    void rejectsStatsAndClosingWhileAuctionIsOpen() {
        league.setAuctionOpen(true);
        Matchday day = Matchday.builder().id(1L).numero(1).league(league).build();
        when(matchdayRepository.findById(1L)).thenReturn(Optional.of(day));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(league.getAdmin());

        assertThatThrownBy(() -> service.inserisciStatistiche("creator", 1L,
                new PlayerStatRequest(10L, 0, 0, 0, 0, false)))
                .isInstanceOf(BusinessRuleException.class).hasMessageContaining("asta");
        assertThatThrownBy(() -> service.chiudiGiornata("creator", 1L))
                .isInstanceOf(BusinessRuleException.class).hasMessageContaining("asta");
    }
}
