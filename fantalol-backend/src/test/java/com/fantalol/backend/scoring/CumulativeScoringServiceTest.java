package com.fantalol.backend.scoring;

import com.fantalol.backend.integration.oracle.ProviderGame;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStatRepository;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.lineup.EffectiveLineupPeriod;
import com.fantalol.backend.lineup.EffectiveLineupPeriodRepository;
import com.fantalol.backend.scoring.dto.FantasyRoleSlotScore;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class CumulativeScoringServiceTest {

    private static final Long TEAM_ID = 7L;
    private static final Instant FRIDAY = Instant.parse("2026-07-31T00:00:00Z");

    @Mock private ProviderPlayerGameStatRepository statRepository;
    @Mock private FantaTeamRepository fantaTeamRepository;
    @Mock private EffectiveLineupPeriodRepository lineupPeriodRepository;

    private CumulativeScoringService service;
    private FantaTeam team;
    private LecPlayer oldMid;
    private LecPlayer newMid;
    private LecPlayer benchMid;
    private Map<PlayerRole, LecPlayer> starters;

    @BeforeEach
    void setUp() {
        service = new CumulativeScoringService(statRepository, fantaTeamRepository, lineupPeriodRepository);
        team = FantaTeam.builder().id(TEAM_ID).nome("Blue Phoenix").build();
        oldMid = player(11L, "Old Mid", PlayerRole.MID);
        newMid = player(12L, "New Mid", PlayerRole.MID);
        benchMid = player(13L, "Bench Mid", PlayerRole.MID);
        starters = new EnumMap<>(PlayerRole.class);
        starters.put(PlayerRole.TOP, player(21L, "Top", PlayerRole.TOP));
        starters.put(PlayerRole.JUNGLE, player(22L, "Jungle", PlayerRole.JUNGLE));
        starters.put(PlayerRole.MID, oldMid);
        starters.put(PlayerRole.ADC, player(23L, "Adc", PlayerRole.ADC));
        starters.put(PlayerRole.SUPPORT, player(24L, "Support", PlayerRole.SUPPORT));

        List<ProviderPlayerGameStat> stats = List.of(
                stat(oldMid, "2026-07-28T12:00:00Z", 10.0),
                stat(oldMid, "2026-07-29T12:00:00Z", 20.0),
                stat(oldMid, "2026-07-30T12:00:00Z", 30.0),
                stat(newMid, "2026-08-01T12:00:00Z", 40.0),
                stat(benchMid, "2026-07-29T12:00:00Z", 100.0),
                stat(starters.get(PlayerRole.TOP), "2026-07-29T12:00:00Z", 11.0),
                stat(starters.get(PlayerRole.JUNGLE), "2026-07-29T12:00:00Z", 12.0),
                stat(starters.get(PlayerRole.ADC), "2026-07-29T12:00:00Z", 13.0));
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(stats);
        lenient().when(fantaTeamRepository.findById(TEAM_ID)).thenReturn(Optional.of(team));
        lenient().when(lineupPeriodRepository.findByFantaTeamIdIn(anyCollection())).thenReturn(List.of(
                period(team, PlayerRole.TOP, starters.get(PlayerRole.TOP), Instant.EPOCH, null),
                period(team, PlayerRole.JUNGLE, starters.get(PlayerRole.JUNGLE), Instant.EPOCH, null),
                period(team, PlayerRole.MID, oldMid, Instant.EPOCH, FRIDAY),
                period(team, PlayerRole.MID, newMid, FRIDAY, null),
                period(team, PlayerRole.ADC, starters.get(PlayerRole.ADC), Instant.EPOCH, null),
                period(team, PlayerRole.SUPPORT, starters.get(PlayerRole.SUPPORT), Instant.EPOCH, null)));
    }

    @Test
    void playerAverageUsesOnlyGamesActuallyPlayedRegardlessOfLineupStatus() {
        var score = service.playerScore(oldMid.getId());

        assertThat(score.gamesPlayed()).isEqualTo(3);
        assertThat(score.average()).isEqualTo(20.0);
        assertThat(service.playerScore(benchMid.getId()).average()).isEqualTo(100.0);
    }

    @Test
    void teamAttributesOnlyThePlayerActiveWhenEachGameWasPlayed() {
        FantasyRoleSlotScore mid = service.teamScore(TEAM_ID).slots().stream()
                .filter(slot -> slot.role() == PlayerRole.MID)
                .findFirst()
                .orElseThrow();

        assertThat(mid.gamesPlayed()).isEqualTo(4);
        assertThat(mid.average()).isEqualTo(25.0);
        assertThat(mid.contributingPlayers()).containsExactly("Old Mid", "New Mid");
        verify(statRepository, times(1)).findAllByOrderByProviderGamePlayedAtAsc();
        verify(lineupPeriodRepository, times(1)).findByFantaTeamIdIn(anyCollection());
        verify(lineupPeriodRepository, never()).findActiveByFantaTeamIdAndRole(anyLong(), any(), any());
    }

    @Test
    void teamWithoutAnObservationForOneStarterIsProvisionalInsteadOfUsingZero() {
        var score = service.teamScore(TEAM_ID);
        FantasyRoleSlotScore support = score.slots().stream()
                .filter(slot -> slot.role() == PlayerRole.SUPPORT)
                .findFirst()
                .orElseThrow();

        assertThat(score.slots()).extracting(FantasyRoleSlotScore::role)
                .containsExactlyInAnyOrder(PlayerRole.values());
        assertThat(support.gamesPlayed()).isZero();
        assertThat(support.average()).isNull();
        assertThat(support.status()).isEqualTo("awaiting-data");
        assertThat(score.overallTotal()).isNull();
        assertThat(score.provisional()).isTrue();
    }

    @Test
    void teamTotalSumsEveryParticipatedGameForTheHistoricallyActiveRoster() {
        ProviderPlayerGameStat support = stat(starters.get(PlayerRole.SUPPORT), "2026-07-29T12:00:00Z", 14.0);
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(List.of(
                stat(starters.get(PlayerRole.TOP), "2026-07-29T12:00:00Z", 11.0),
                stat(starters.get(PlayerRole.JUNGLE), "2026-07-29T12:00:00Z", 12.0),
                stat(oldMid, "2026-07-29T12:00:00Z", 10.0),
                stat(newMid, "2026-08-01T12:00:00Z", 40.0),
                stat(starters.get(PlayerRole.ADC), "2026-07-29T12:00:00Z", 13.0),
                support));

        assertThat(service.teamScore(TEAM_ID).overallTotal()).isEqualTo(100.0);
    }

    @Test
    void currentAdminCorrectionCanActivateARawNonparticipant() {
        ProviderPlayerGameStat corrected = stat(oldMid, "2026-07-28T12:00:00Z", 25.0);
        corrected.setRawParticipated(false);
        corrected.setCorrectedParticipated(true);
        corrected.setSourceFingerprint("current");
        corrected.getProviderGame().setSourceFingerprint("current");
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(List.of(corrected));

        assertThat(service.playerScore(oldMid.getId()))
                .extracting(
                        score -> score.gamesPlayed(),
                        score -> score.average())
                .containsExactly(1, 25.0);
    }

    @Test
    void removedProviderRowStillContributesWhileItsOverrideParticipates() {
        ProviderPlayerGameStat stale = stat(oldMid, "2026-07-28T12:00:00Z", 25.0);
        stale.setOverridden(true);
        stale.setCorrectedParticipated(true);
        stale.setSourceFingerprint("former");
        stale.getProviderGame().setSourceFingerprint("current");
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(List.of(stale));

        assertThat(service.playerScore(oldMid.getId()))
                .extracting(
                        score -> score.gamesPlayed(),
                        score -> score.average())
                .containsExactly(1, 25.0);
    }

    @Test
    void removedProviderRowDoesNotContributeWhenItsOverrideMarksNonparticipation() {
        ProviderPlayerGameStat stale = stat(oldMid, "2026-07-28T12:00:00Z", 25.0);
        stale.setOverridden(true);
        stale.setCorrectedParticipated(false);
        stale.setSourceFingerprint("former");
        stale.getProviderGame().setSourceFingerprint("current");
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(List.of(stale));

        assertThat(service.playerScores()).isEmpty();
    }

    @Test
    void leagueRankingBatchLoadsObservationsAndPeriodsWhilePreservingAttributionAndOrder() {
        FantaTeam zeta = FantaTeam.builder().id(8L).nome("Zeta").build();
        FantaTeam ghost = FantaTeam.builder().id(9L).nome("Ghost").build();
        List<LecPlayer> zetaPlayers = List.of(
                player(31L, "Zeta Top", PlayerRole.TOP),
                player(32L, "Zeta Jungle", PlayerRole.JUNGLE),
                player(33L, "Zeta Mid", PlayerRole.MID),
                player(34L, "Zeta Adc", PlayerRole.ADC),
                player(35L, "Zeta Support", PlayerRole.SUPPORT));
        List<ProviderPlayerGameStat> observations = List.of(
                stat(starters.get(PlayerRole.TOP), "2026-07-29T12:00:00Z", 10.0),
                stat(starters.get(PlayerRole.JUNGLE), "2026-07-29T12:00:00Z", 10.0),
                stat(oldMid, "2026-07-29T12:00:00Z", 10.0),
                stat(newMid, "2026-08-01T12:00:00Z", 30.0),
                stat(starters.get(PlayerRole.ADC), "2026-07-29T12:00:00Z", 10.0),
                stat(starters.get(PlayerRole.SUPPORT), "2026-07-29T12:00:00Z", 10.0),
                stat(zetaPlayers.get(0), "2026-07-29T12:00:00Z", 50.0),
                stat(zetaPlayers.get(1), "2026-07-29T12:00:00Z", 50.0),
                stat(zetaPlayers.get(2), "2026-07-29T12:00:00Z", 50.0),
                stat(zetaPlayers.get(3), "2026-07-29T12:00:00Z", 50.0),
                stat(zetaPlayers.get(4), "2026-07-29T12:00:00Z", 50.0));
        List<EffectiveLineupPeriod> periods = List.of(
                period(team, PlayerRole.TOP, starters.get(PlayerRole.TOP), Instant.EPOCH, null),
                period(team, PlayerRole.JUNGLE, starters.get(PlayerRole.JUNGLE), Instant.EPOCH, null),
                period(team, PlayerRole.MID, oldMid, Instant.EPOCH, FRIDAY),
                period(team, PlayerRole.MID, newMid, FRIDAY, null),
                period(team, PlayerRole.ADC, starters.get(PlayerRole.ADC), Instant.EPOCH, null),
                period(team, PlayerRole.SUPPORT, starters.get(PlayerRole.SUPPORT), Instant.EPOCH, null),
                period(zeta, PlayerRole.TOP, zetaPlayers.get(0), Instant.EPOCH, null),
                period(zeta, PlayerRole.JUNGLE, zetaPlayers.get(1), Instant.EPOCH, null),
                period(zeta, PlayerRole.MID, zetaPlayers.get(2), Instant.EPOCH, null),
                period(zeta, PlayerRole.ADC, zetaPlayers.get(3), Instant.EPOCH, null),
                period(zeta, PlayerRole.SUPPORT, zetaPlayers.get(4), Instant.EPOCH, null),
                period(ghost, PlayerRole.TOP, starters.get(PlayerRole.TOP), Instant.EPOCH, null),
                period(ghost, PlayerRole.JUNGLE, starters.get(PlayerRole.JUNGLE), Instant.EPOCH, null),
                period(ghost, PlayerRole.MID, oldMid, Instant.EPOCH, null),
                period(ghost, PlayerRole.ADC, starters.get(PlayerRole.ADC), Instant.EPOCH, null));
        when(fantaTeamRepository.findByLeagueId(5L)).thenReturn(List.of(team, zeta, ghost));
        lenient().when(fantaTeamRepository.findById(8L)).thenReturn(Optional.of(zeta));
        lenient().when(fantaTeamRepository.findById(9L)).thenReturn(Optional.of(ghost));
        when(statRepository.findAllByOrderByProviderGamePlayedAtAsc()).thenReturn(observations);
        when(lineupPeriodRepository.findByFantaTeamIdIn(anyCollection())).thenReturn(periods);

        var ranking = service.leagueRanking(5L);

        assertThat(ranking).extracting(score -> score.teamName())
                .containsExactly("Zeta", "Blue Phoenix", "Ghost");
        assertThat(ranking.get(1).slots().stream()
                .filter(slot -> slot.role() == PlayerRole.MID)
                .findFirst().orElseThrow().contributingPlayers())
                .containsExactly("Old Mid", "New Mid");
        assertThat(ranking.get(2).provisional()).isTrue();
        verify(fantaTeamRepository, times(1)).findByLeagueId(5L);
        verify(statRepository, times(1)).findAllByOrderByProviderGamePlayedAtAsc();
        verify(lineupPeriodRepository, times(1)).findByFantaTeamIdIn(anyCollection());
        verify(fantaTeamRepository, never()).findById(anyLong());
        verify(lineupPeriodRepository, never()).findActiveByFantaTeamIdAndRole(anyLong(), any(), any());
    }

    private LecPlayer player(Long id, String nickname, PlayerRole role) {
        return LecPlayer.builder().id(id).nickname(nickname).ruolo(role).build();
    }

    private ProviderPlayerGameStat stat(LecPlayer player, String playedAt, double score) {
        return ProviderPlayerGameStat.builder()
                .lecPlayer(player)
                .providerGame(ProviderGame.builder().id(player.getId() * 100 + playedAt.hashCode()).playedAt(Instant.parse(playedAt)).build())
                .rawParticipated(true)
                .fantasyScore(score)
                .build();
    }

    private EffectiveLineupPeriod period(FantaTeam fantasyTeam, PlayerRole role, LecPlayer player,
                                         Instant effectiveFrom, Instant effectiveUntil) {
        return EffectiveLineupPeriod.builder().fantaTeam(fantasyTeam).role(role).lecPlayer(player)
                .effectiveFrom(effectiveFrom).effectiveUntil(effectiveUntil).build();
    }
}
