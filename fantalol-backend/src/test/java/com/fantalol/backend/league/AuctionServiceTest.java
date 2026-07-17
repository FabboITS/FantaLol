package com.fantalol.backend.league;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.league.dto.AuctionBidRequest;
import com.fantalol.backend.league.dto.AuctionStartRequest;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuctionServiceTest {
    @Mock AuctionSessionRepository auctionRepository;
    @Mock LeagueRepository leagueRepository;
    @Mock FantaTeamRepository fantaTeamRepository;
    @Mock RosterEntryRepository rosterRepository;
    @Mock LecPlayerRepository playerRepository;
    @Mock UserService userService;
    @Mock RosterPolicy rosterPolicy;
    @InjectMocks AuctionService auctionService;

    @Test
    void cannotNominateWhileLeagueAuctionIsClosed() {
        League league = League.builder().id(1L).auctionOpen(false).build();
        when(leagueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(league));

        assertThatThrownBy(() -> auctionService.start("owner", new AuctionStartRequest(1L, 10L, 20L)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("L'asta della lega non è aperta");
    }

    @Test
    void cannotBidWhileLeagueAuctionIsClosed() {
        League league = League.builder().id(1L).auctionOpen(false).build();
        AuctionSession auction = AuctionSession.builder().id(2L).league(league)
                .status(AuctionStatus.ACTIVE).endsAt(Instant.now().plusSeconds(10)).build();
        when(auctionRepository.findByIdForUpdate(2L)).thenReturn(Optional.of(auction));

        assertThatThrownBy(() -> auctionService.bid("owner", 2L, new AuctionBidRequest(20L, 200)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("L'asta della lega non è aperta");
    }

    @Test
    void acceptsAFullCreditCustomBidAndRejectsTheNextRelaunch() {
        League league = League.builder().id(1L).auctionOpen(true).build();
        User owner = User.builder().username("owner").role(Role.USER).build();
        FantaTeam team = FantaTeam.builder().id(20L).nome("Team").league(league)
                .owner(owner).creditiResidui(1000).build();
        LecPlayer player = LecPlayer.builder().id(10L).nickname("Caps")
                .ruolo(PlayerRole.MID).quotazione(100).build();
        AuctionSession auction = AuctionSession.builder().id(2L).league(league).player(player)
                .highestBidder(team).currentBid(100).status(AuctionStatus.ACTIVE)
                .endsAt(Instant.now().plusSeconds(10)).build();
        when(auctionRepository.findByIdForUpdate(2L)).thenReturn(Optional.of(auction));
        when(fantaTeamRepository.findById(20L)).thenReturn(Optional.of(team));
        when(rosterRepository.findByFantaTeamId(20L)).thenReturn(java.util.List.of());
        when(rosterPolicy.forLeague(league)).thenReturn(new RosterPolicy.Limits(10, 2));
        when(auctionRepository.save(any(AuctionSession.class))).thenAnswer(invocation -> invocation.getArgument(0));

        assertThat(auctionService.bid("owner", 2L, new AuctionBidRequest(20L, 1000)).currentBid())
                .isEqualTo(1000);
        assertThatThrownBy(() -> auctionService.bid("owner", 2L, new AuctionBidRequest(20L, 1001)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("Crediti insufficienti");
    }
}
