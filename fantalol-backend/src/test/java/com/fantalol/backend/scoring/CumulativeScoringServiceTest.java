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
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
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
        lenient().when(lineupPeriodRepository.findActiveByFantaTeamIdAndRole(eq(TEAM_ID), any(), any()))
                .thenAnswer(invocation -> {
                    PlayerRole role = invocation.getArgument(1);
                    Instant playedAt = invocation.getArgument(2);
                    LecPlayer player = role == PlayerRole.MID && !playedAt.isBefore(FRIDAY)
                            ? newMid : starters.get(role);
                    return Optional.of(period(role, player));
                });
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
        assertThat(score.overallAverage()).isNull();
        assertThat(score.provisional()).isTrue();
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

    private EffectiveLineupPeriod period(PlayerRole role, LecPlayer player) {
        return EffectiveLineupPeriod.builder().fantaTeam(team).role(role).lecPlayer(player)
                .effectiveFrom(Instant.EPOCH).build();
    }
}
