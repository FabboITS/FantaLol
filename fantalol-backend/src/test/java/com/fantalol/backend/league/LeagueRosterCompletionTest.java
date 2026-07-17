package com.fantalol.backend.league;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class LeagueRosterCompletionTest {
    @Mock LeagueRepository leagueRepository;
    @Mock UserService userService;
    @Mock AuctionSessionRepository auctionSessionRepository;
    @Mock FantaTeamRepository fantaTeamRepository;
    @Mock RosterEntryRepository rosterEntryRepository;
    @Mock LecPlayerRepository lecPlayerRepository;
    @Mock RosterPolicy rosterPolicy;
    @InjectMocks LeagueService leagueService;

    private User creator;
    private League league;
    private FantaTeam team;

    @BeforeEach
    void setUp() {
        creator = User.builder().id(1L).username("creator").role(Role.USER).build();
        league = League.builder().id(1L).nome("LEC").admin(creator).auctionOpen(false).build();
        team = FantaTeam.builder().id(2L).nome("Team").league(league).owner(creator)
                .creditiResidui(1000).rosa(new ArrayList<>()).build();
    }

    @Test
    void creatorCompletesEveryMissingRoleForEveryTeam() {
        when(leagueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(league));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(creator);
        when(fantaTeamRepository.findByLeagueId(1L)).thenReturn(List.of(team));
        when(rosterPolicy.forLeague(league)).thenReturn(new RosterPolicy.Limits(10, 2));
        when(rosterEntryRepository.findByFantaTeamId(2L)).thenReturn(List.of());
        List<LecPlayer> players = Stream.of(PlayerRole.values())
                .flatMap(role -> Stream.of(0, 1).map(i -> LecPlayer.builder()
                        .id((long) role.ordinal() * 2 + i + 1).nickname(role + "-" + i).ruolo(role).build()))
                .toList();
        when(lecPlayerRepository.findAll()).thenReturn(players);
        when(rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(any(), any())).thenReturn(false);
        AtomicLong ids = new AtomicLong(1);
        when(rosterEntryRepository.save(any(RosterEntry.class))).thenAnswer(invocation -> {
            RosterEntry entry = invocation.getArgument(0);
            entry.setId(ids.getAndIncrement());
            return entry;
        });

        var result = leagueService.completeAllRostersRandomly("creator", 1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).rosa()).hasSize(10);
        assertThat(result.get(0).rosa()).allMatch(entry -> entry.creditiSpesi() == 0);
    }

    @Test
    void randomCompletionIsRejectedWhileAuctionIsOpen() {
        league.setAuctionOpen(true);
        when(leagueRepository.findByIdForUpdate(1L)).thenReturn(Optional.of(league));
        when(userService.findByUsernameOrThrow("creator")).thenReturn(creator);

        assertThatThrownBy(() -> leagueService.completeAllRostersRandomly("creator", 1L))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("Termina l'asta della lega prima di completare casualmente le rose");
    }
}
