package com.fantalol.backend.league;

import com.fantalol.backend.league.dto.LeagueResponse;
import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.user.Role;
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
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class LeagueAuctionPhaseServiceTest {

    @Mock private LeagueRepository leagueRepository;
    @Mock private UserService userService;
    @Mock private AuctionSessionRepository auctionSessionRepository;
    @InjectMocks private LeagueService leagueService;

    private User creator;
    private League league;

    @BeforeEach
    void setUp() {
        creator = User.builder().username("creator").role(Role.USER).build();
        league = League.builder().id(1L).nome("LEC").codiceInvito("ABC")
                .creditiIniziali(1000).admin(creator).auctionOpen(false).build();
    }

    @Test
    void responseExposesAuctionPhaseState() {
        League closed = League.builder().id(1L).nome("LEC").codiceInvito("ABC")
                .creditiIniziali(1000).admin(creator).auctionOpen(false).build();
        League open = League.builder().id(2L).nome("Open").codiceInvito("DEF")
                .creditiIniziali(1000).admin(creator).auctionOpen(true).build();

        assertThat(LeagueResponse.from(closed).auctionOpen()).isFalse();
        assertThat(LeagueResponse.from(open).auctionOpen()).isTrue();
    }

    @Test
    void creatorCanOpenCloseAndReopenAuction() {
        when(leagueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(league));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(creator);
        when(leagueRepository.save(any(League.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(auctionSessionRepository.findFirstByLeagueIdAndStatus(1L, AuctionStatus.ACTIVE))
                .thenReturn(Optional.empty());

        assertThat(leagueService.openAuction("creator", 1L).auctionOpen()).isTrue();
        assertThat(leagueService.closeAuction("creator", 1L).auctionOpen()).isFalse();
        assertThat(leagueService.openAuction("creator", 1L).auctionOpen()).isTrue();
    }

    @Test
    void participantCannotOpenAuction() {
        User participant = User.builder().username("participant").role(Role.USER).build();
        when(leagueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(league));
        when(userService.findByUsernameOrThrow("participant")).thenReturn(participant);

        assertThatThrownBy(() -> leagueService.openAuction("participant", 1L))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("Solo il creatore della lega può gestire l'asta");
    }

    @Test
    void closeIsRejectedWhilePlayerAuctionIsActive() {
        league.setAuctionOpen(true);
        when(leagueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(league));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(creator);
        when(auctionSessionRepository.findFirstByLeagueIdAndStatus(1L, AuctionStatus.ACTIVE))
                .thenReturn(Optional.of(AuctionSession.builder().status(AuctionStatus.ACTIVE).build()));

        assertThatThrownBy(() -> leagueService.closeAuction("creator", 1L))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("Attendi la fine dell'asta del player prima di terminare l'asta della lega");
        assertThat(league.isAuctionOpen()).isTrue();
    }
}
