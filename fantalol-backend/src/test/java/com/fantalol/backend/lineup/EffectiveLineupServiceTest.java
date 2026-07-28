package com.fantalol.backend.lineup;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.League;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class EffectiveLineupServiceTest {

    @Mock
    private EffectiveLineupPeriodRepository periodRepository;
    @Mock
    private FantaTeamRepository fantaTeamRepository;
    @Mock
    private UserService userService;
    @Captor
    private ArgumentCaptor<List<EffectiveLineupPeriod>> savedPeriods;

    private EffectiveLineupService service;
    private FantaTeam fantaTeam;
    private Set<LecPlayer> players;

    @BeforeEach
    void setUp() {
        Clock clock = Clock.fixed(Instant.parse("2026-07-29T10:00:00Z"), ZoneOffset.UTC);
        service = new EffectiveLineupService(periodRepository, fantaTeamRepository, userService,
                new LineupWindow(), clock);
        fantaTeam = FantaTeam.builder().id(7L).owner(User.builder().username("mago").build())
                .league(League.builder().participantCount(5).build()).build();
        players = Set.of(
                player(11L, PlayerRole.TOP), player(12L, PlayerRole.JUNGLE), player(13L, PlayerRole.MID),
                player(14L, PlayerRole.ADC), player(15L, PlayerRole.SUPPORT));
    }

    @Test
    void schedulesFiveRolePeriodsAtFridayAndClosesTheCurrentPeriods() {
        List<EffectiveLineupPeriod> current = players.stream()
                .map(player -> EffectiveLineupPeriod.builder().fantaTeam(fantaTeam).role(player.getRuolo())
                        .lecPlayer(player).effectiveFrom(Instant.parse("2026-07-24T00:00:00Z"))
                        .origin(LineupPeriodOrigin.USER).build())
                .toList();
        when(fantaTeamRepository.findById(7L)).thenReturn(Optional.of(fantaTeam));
        when(periodRepository.findByFantaTeamIdAndEffectiveUntilIsNull(7L)).thenReturn(current);
        when(periodRepository.saveAll(anyList())).thenAnswer(invocation -> invocation.getArgument(0));

        service.schedule("mago", 7L, players);

        org.mockito.Mockito.verify(periodRepository).saveAll(savedPeriods.capture());
        Instant friday = Instant.parse("2026-07-30T22:00:00Z");
        assertThat(current).allSatisfy(period -> assertThat(period.getEffectiveUntil()).isEqualTo(friday));
        assertThat(savedPeriods.getValue()).filteredOn(period -> period.getEffectiveFrom().equals(friday))
                .hasSize(5)
                .allSatisfy(period -> assertThat(period.getOrigin()).isEqualTo(LineupPeriodOrigin.USER));
    }

    @Test
    void replacesPendingFridayPeriodsWhenTheLineupIsSavedAgainBeforeFriday() {
        Instant friday = Instant.parse("2026-07-30T22:00:00Z");
        List<EffectiveLineupPeriod> pending = players.stream()
                .map(player -> EffectiveLineupPeriod.builder().fantaTeam(fantaTeam).role(player.getRuolo())
                        .lecPlayer(player).effectiveFrom(friday).origin(LineupPeriodOrigin.USER).build())
                .toList();
        when(fantaTeamRepository.findById(7L)).thenReturn(Optional.of(fantaTeam));
        when(periodRepository.findByFantaTeamIdAndEffectiveUntilIsNull(7L)).thenReturn(pending);
        when(periodRepository.saveAll(anyList())).thenAnswer(invocation -> invocation.getArgument(0));

        service.schedule("mago", 7L, players);

        verify(periodRepository).deleteAll(pending);
        verify(periodRepository).flush();
        verify(periodRepository).saveAll(savedPeriods.capture());
        assertThat(pending).allSatisfy(period -> assertThat(period.getEffectiveUntil()).isNull());
        assertThat(savedPeriods.getValue()).hasSize(5)
                .allSatisfy(period -> assertThat(period.getEffectiveFrom()).isEqualTo(friday));
    }

    @Test
    void rejectsSchedulingOutsideTheRomeEditingWindow() {
        Clock friday = Clock.fixed(Instant.parse("2026-07-31T10:00:00Z"), ZoneOffset.UTC);
        service = new EffectiveLineupService(periodRepository, fantaTeamRepository, userService,
                new LineupWindow(), friday);
        when(fantaTeamRepository.findById(7L)).thenReturn(Optional.of(fantaTeam));

        assertThatThrownBy(() -> service.schedule("mago", 7L, players))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("martedì");
    }

    @Test
    void rejectsSchedulingForFixedRosterLeagues() {
        fantaTeam.getLeague().setParticipantCount(6);
        when(fantaTeamRepository.findById(7L)).thenReturn(Optional.of(fantaTeam));

        assertThatThrownBy(() -> service.schedule("mago", 7L, players))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("almeno 6");
    }

    @Test
    void returnsThePlayerActiveForThePlayedInstant() {
        LecPlayer mid = player(13L, PlayerRole.MID);
        EffectiveLineupPeriod period = EffectiveLineupPeriod.builder().fantaTeam(fantaTeam).role(PlayerRole.MID)
                .lecPlayer(mid).effectiveFrom(Instant.parse("2026-07-31T00:00:00Z"))
                .origin(LineupPeriodOrigin.USER).build();
        when(periodRepository.findActiveByFantaTeamIdAndRole(7L, PlayerRole.MID, Instant.parse("2026-08-01T10:00:00Z")))
                .thenReturn(Optional.of(period));

        assertThat(service.activePeriodAt(7L, PlayerRole.MID, Instant.parse("2026-08-01T10:00:00Z")))
                .contains(period);
    }

    private LecPlayer player(Long id, PlayerRole role) {
        return LecPlayer.builder().id(id).nickname(role.name()).ruolo(role).build();
    }
}
