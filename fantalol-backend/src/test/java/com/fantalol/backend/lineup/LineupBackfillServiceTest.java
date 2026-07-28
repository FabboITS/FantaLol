package com.fantalol.backend.lineup;

import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.League;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.matchday.Formation;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.matchday.FormationSource;
import com.fantalol.backend.matchday.Matchday;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Set;

import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anySet;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class LineupBackfillServiceTest {

    @Mock
    private FantaTeamRepository fantaTeamRepository;
    @Mock
    private RosterEntryRepository rosterEntryRepository;
    @Mock
    private FormationRepository formationRepository;
    @Mock
    private EffectiveLineupPeriodRepository periodRepository;
    @Mock
    private EffectiveLineupService effectiveLineupService;
    @InjectMocks
    private LineupBackfillService backfillService;

    @Test
    void skipsInvalidLatestFormationAndBackfillsAnotherTeamWithItsLatestValidFormation() {
        FantaTeam invalidTeam = team(1L);
        FantaTeam validTeam = team(2L);
        Set<LecPlayer> validPlayers = lineup();
        Formation invalid = Formation.builder().fantaTeam(invalidTeam)
                .matchday(Matchday.builder().numero(2).build()).source(FormationSource.SUBMITTED)
                .titolari(Set.of(player(1L, PlayerRole.TOP))).build();
        Formation newerMissing = Formation.builder().fantaTeam(validTeam)
                .matchday(Matchday.builder().numero(3).build()).source(FormationSource.MISSING).build();
        Formation valid = Formation.builder().fantaTeam(validTeam)
                .matchday(Matchday.builder().numero(1).build()).source(FormationSource.SUBMITTED)
                .titolari(validPlayers).build();
        when(fantaTeamRepository.findAll()).thenReturn(List.of(invalidTeam, validTeam));
        when(periodRepository.existsByFantaTeamId(anyLong())).thenReturn(false);
        when(formationRepository.findByFantaTeamIdOrderByMatchdayNumeroDesc(1L)).thenReturn(List.of(invalid));
        when(formationRepository.findByFantaTeamIdOrderByMatchdayNumeroDesc(2L)).thenReturn(List.of(newerMissing, valid));

        backfillService.backfill();

        verify(effectiveLineupService, never()).createBackfillPeriods(eq(invalidTeam), anySet(),
                eq(LineupBackfillService.BACKFILL_FROM));
        verify(effectiveLineupService).createBackfillPeriods(validTeam, validPlayers, LineupBackfillService.BACKFILL_FROM);
    }

    private FantaTeam team(Long id) {
        return FantaTeam.builder().id(id).league(League.builder().participantCount(5).build()).build();
    }

    private Set<LecPlayer> lineup() {
        return Set.of(
                player(11L, PlayerRole.TOP), player(12L, PlayerRole.JUNGLE), player(13L, PlayerRole.MID),
                player(14L, PlayerRole.ADC), player(15L, PlayerRole.SUPPORT));
    }

    private LecPlayer player(Long id, PlayerRole role) {
        return LecPlayer.builder().id(id).ruolo(role).build();
    }
}
