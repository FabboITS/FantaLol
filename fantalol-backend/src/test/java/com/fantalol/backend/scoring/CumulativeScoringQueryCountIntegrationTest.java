package com.fantalol.backend.scoring;

import com.fantalol.backend.integration.oracle.ProviderGame;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStat;
import com.fantalol.backend.integration.oracle.ProviderPlayerGameStatRepository;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.League;
import com.fantalol.backend.lineup.EffectiveLineupPeriod;
import com.fantalol.backend.lineup.LineupPeriodOrigin;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecTeam;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.User;
import jakarta.persistence.EntityManagerFactory;
import org.hibernate.SessionFactory;
import org.hibernate.stat.Statistics;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest(showSql = false, properties = {
        "spring.jpa.properties.hibernate.generate_statistics=true",
        "logging.level.org.hibernate.engine.internal.StatisticalLoggingSessionEventListener=OFF"
})
@ActiveProfiles("test")
@Import(CumulativeScoringService.class)
class CumulativeScoringQueryCountIntegrationTest {

    @Autowired
    private TestEntityManager entityManager;
    @Autowired
    private EntityManagerFactory entityManagerFactory;
    @Autowired
    private ProviderPlayerGameStatRepository statRepository;
    @Autowired
    private CumulativeScoringService scoringService;

    private Statistics statistics;
    private Fixture fixture;

    @BeforeEach
    void setUp() {
        statistics = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
        statistics.setStatisticsEnabled(true);
        fixture = persistFixture();
        entityManager.flush();
        entityManager.clear();
        statistics.clear();
    }

    @Test
    void observationQueryFetchesGamesAndPlayersInOneOrderedStatement() {
        List<ProviderPlayerGameStat> observations =
                statRepository.findAllByOrderByProviderGamePlayedAtAsc();

        assertThat(observations)
                .extracting(observation -> observation.getProviderGame().getPlayedAt())
                .containsExactly(
                        Instant.parse("2026-07-28T09:00:00Z"),
                        Instant.parse("2026-07-28T09:00:00Z"),
                        Instant.parse("2026-07-29T09:00:00Z"),
                        Instant.parse("2026-07-29T09:00:00Z"));
        assertThat(observations)
                .extracting(observation -> observation.getLecPlayer().getNickname())
                .containsExactlyInAnyOrder("Alpha", "Beta", "Alpha", "Beta");
        assertThat(statistics.getPrepareStatementCount()).isEqualTo(1L);
    }

    @Test
    void leagueRankingKeepsItsThreeBatchStatementsAfterAssociationTraversal() {
        var ranking = scoringService.leagueRanking(fixture.leagueId());

        assertThat(ranking).singleElement()
                .extracting(score -> score.teamName())
                .isEqualTo("Query Count Team");
        assertThat(ranking.get(0).slots().stream()
                .filter(slot -> slot.role() == PlayerRole.TOP)
                .findFirst().orElseThrow().contributingPlayers())
                .containsExactly("Alpha");
        assertThat(statistics.getPrepareStatementCount()).isEqualTo(3L);
    }

    private Fixture persistFixture() {
        User owner = entityManager.persist(User.builder()
                .username("query-owner")
                .email("query-owner@test.local")
                .password("encoded")
                .build());
        League league = entityManager.persist(League.builder()
                .nome("Query League")
                .creditiIniziali(1000)
                .admin(owner)
                .build());
        FantaTeam fantasyTeam = entityManager.persist(FantaTeam.builder()
                .nome("Query Count Team")
                .creditiResidui(1000)
                .league(league)
                .owner(owner)
                .build());
        LecTeam lecTeam = entityManager.persist(LecTeam.builder().nome("Query LEC Team").build());
        LecPlayer alpha = entityManager.persist(player("Alpha", "alpha", PlayerRole.TOP, lecTeam));
        LecPlayer beta = entityManager.persist(player("Beta", "beta", PlayerRole.MID, lecTeam));
        ProviderGame first = entityManager.persist(game("QUERY-GAME-1", "2026-07-28T09:00:00Z"));
        ProviderGame second = entityManager.persist(game("QUERY-GAME-2", "2026-07-29T09:00:00Z"));
        entityManager.persist(period(fantasyTeam, alpha));
        entityManager.persist(period(fantasyTeam, beta));
        entityManager.persist(stat(first, alpha, 10.0));
        entityManager.persist(stat(first, beta, 20.0));
        entityManager.persist(stat(second, alpha, 30.0));
        entityManager.persist(stat(second, beta, 40.0));
        return new Fixture(league.getId());
    }

    private LecPlayer player(String nickname, String oracleId, PlayerRole role, LecTeam team) {
        return LecPlayer.builder()
                .nickname(nickname)
                .oraclePlayerId(oracleId)
                .ruolo(role)
                .quotazione(10)
                .team(team)
                .build();
    }

    private ProviderGame game(String externalId, String playedAt) {
        return ProviderGame.builder()
                .externalGameId(externalId)
                .playedAt(Instant.parse(playedAt))
                .league("LEC")
                .split("Summer")
                .sourceFingerprint(externalId + "-fingerprint")
                .build();
    }

    private EffectiveLineupPeriod period(FantaTeam fantasyTeam, LecPlayer player) {
        return EffectiveLineupPeriod.builder()
                .fantaTeam(fantasyTeam)
                .role(player.getRuolo())
                .lecPlayer(player)
                .effectiveFrom(Instant.EPOCH)
                .origin(LineupPeriodOrigin.BACKFILL)
                .createdAt(Instant.EPOCH)
                .build();
    }

    private ProviderPlayerGameStat stat(ProviderGame game, LecPlayer player, double fantasyScore) {
        return ProviderPlayerGameStat.builder()
                .providerGame(game)
                .lecPlayer(player)
                .externalPlayerId(player.getOraclePlayerId())
                .sourceNickname(player.getNickname())
                .sourceTeamName(player.getTeam().getNome())
                .sourceRole(player.getRuolo())
                .sourceChampion("Champion")
                .sourceFingerprint(game.getSourceFingerprint())
                .rawParticipated(true)
                .fantasyScore(fantasyScore)
                .build();
    }

    private record Fixture(Long leagueId) {
    }
}
