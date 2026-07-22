package com.fantalol.backend.league;

import com.fantalol.backend.league.dto.LeagueResponse;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Sort;
import org.springframework.security.access.AccessDeniedException;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class LeagueVisibilityServiceTest {

    @Mock private LeagueRepository leagueRepository;
    @Mock private UserService userService;
    @Mock private AuctionSessionRepository auctionSessionRepository;
    @Mock private FantaTeamRepository fantaTeamRepository;
    @Mock private RosterEntryRepository rosterEntryRepository;
    @Mock private LecPlayerRepository lecPlayerRepository;
    @Mock private RosterPolicy rosterPolicy;

    @InjectMocks private LeagueService service;

    private User globalAdmin;
    private User alice;
    private User bob;
    private League firstLeague;
    private League secondLeague;

    @BeforeEach
    void setUp() {
        globalAdmin = User.builder().id(1L).username("root-admin").role(Role.ADMIN).build();
        alice = User.builder().id(2L).username("alice").role(Role.USER).build();
        bob = User.builder().id(3L).username("bob").role(Role.USER).build();
        firstLeague = league(1L, "Alpha League", alice);
        secondLeague = league(2L, "Beta League", bob);
    }

    @Test
    void globalAdminListsEveryLeague() {
        when(userService.findByUsernameOrThrow("root-admin")).thenReturn(globalAdmin);
        when(leagueRepository.findAll(Sort.by(Sort.Direction.ASC, "id")))
                .thenReturn(List.of(firstLeague, secondLeague));

        assertThat(service.findAll("root-admin"))
                .extracting(LeagueResponse::id)
                .containsExactly(1L, 2L);
    }

    @Test
    void regularUserListsOnlyCreatedOrJoinedLeaguesWithoutDuplicates() {
        when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);
        when(leagueRepository.findAccessibleByUsername("alice"))
                .thenReturn(List.of(firstLeague, secondLeague));

        assertThat(service.findAll("alice"))
                .extracting(LeagueResponse::id)
                .containsExactly(1L, 2L);
    }

    @Test
    void creatorCanOpenTheirLeague() {
        when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);
        when(leagueRepository.findById(1L)).thenReturn(Optional.of(firstLeague));

        assertThat(service.findById("alice", 1L).id()).isEqualTo(1L);
    }

    @Test
    void joinedUserCanOpenLeague() {
        when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);
        when(leagueRepository.findById(2L)).thenReturn(Optional.of(secondLeague));
        when(fantaTeamRepository.findByLeagueIdAndOwnerUsername(2L, "alice"))
                .thenReturn(Optional.of(FantaTeam.builder().id(10L).league(secondLeague).owner(alice).build()));

        assertThat(service.findById("alice", 2L).id()).isEqualTo(2L);
    }

    @Test
    void regularUserCannotOpenUnrelatedLeague() {
        when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);
        when(leagueRepository.findById(2L)).thenReturn(Optional.of(secondLeague));
        when(fantaTeamRepository.findByLeagueIdAndOwnerUsername(2L, "alice")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.findById("alice", 2L))
                .isInstanceOf(AccessDeniedException.class);
    }

    @Test
    void globalAdminCanDeleteAnyLeague() {
        when(leagueRepository.findById(2L)).thenReturn(Optional.of(secondLeague));
        when(userService.findByUsernameOrThrow("root-admin")).thenReturn(globalAdmin);

        service.delete("root-admin", 2L);

        verify(leagueRepository).delete(secondLeague);
    }

    @Test
    void unrelatedUserCannotDeleteLeague() {
        when(leagueRepository.findById(2L)).thenReturn(Optional.of(secondLeague));
        when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);

        assertThatThrownBy(() -> service.delete("alice", 2L))
                .isInstanceOf(AccessDeniedException.class);
        verify(leagueRepository, never()).delete(any());
    }

    private League league(Long id, String name, User owner) {
        return League.builder()
                .id(id)
                .nome(name)
                .codiceInvito("CODE000" + id)
                .creditiIniziali(1000)
                .admin(owner)
                .fantaTeams(new java.util.ArrayList<>())
                .build();
    }
}
