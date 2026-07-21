package com.fantalol.backend.league;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RosterPolicyTest {
    @Mock private FantaTeamRepository fantaTeamRepository;
    @InjectMocks private RosterPolicy rosterPolicy;

    private final League league = League.builder().id(1L).build();

    @Test
    void sixTeamsUseOnePlayerPerRole() {
        when(fantaTeamRepository.countByLeagueId(1L)).thenReturn(6L);
        assertThat(rosterPolicy.forLeague(league)).isEqualTo(new RosterPolicy.Limits(5, 1));
    }

    @Test
    void fiveTeamsUseTwoPlayersPerRole() {
        when(fantaTeamRepository.countByLeagueId(1L)).thenReturn(5L);
        assertThat(rosterPolicy.forLeague(league)).isEqualTo(new RosterPolicy.Limits(10, 2));
    }

    @Test
    void frozenParticipantCountDoesNotChangeWhenMoreTeamsAreCounted() {
        League frozen = League.builder().id(1L).participantCount(5).build();

        assertThat(rosterPolicy.forLeague(frozen)).isEqualTo(new RosterPolicy.Limits(10, 2));
    }
}
