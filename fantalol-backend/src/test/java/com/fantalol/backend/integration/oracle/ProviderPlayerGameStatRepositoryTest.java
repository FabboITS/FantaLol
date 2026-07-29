package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecTeam;
import com.fantalol.backend.team.PlayerRole;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;
import org.springframework.test.context.ActiveProfiles;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
class ProviderPlayerGameStatRepositoryTest {
    @Autowired
    private TestEntityManager entityManager;
    @Autowired
    private ProviderPlayerGameStatRepository repository;

    @Test
    void returnsCurrentProviderRowWhenAdminCorrectedNonparticipationToParticipated() {
        LecTeam team = entityManager.persist(LecTeam.builder().nome("G2 Esports").build());
        LecPlayer player = entityManager.persist(LecPlayer.builder()
                .nickname("Caps")
                .oraclePlayerId("caps")
                .ruolo(PlayerRole.MID)
                .quotazione(20)
                .team(team)
                .build());
        ProviderGame game = entityManager.persist(ProviderGame.builder()
                .externalGameId("GAME-1")
                .playedAt(Instant.parse("2026-07-28T09:00:00Z"))
                .league("LEC")
                .split("Summer")
                .sourceFingerprint("current")
                .build());
        entityManager.persistAndFlush(ProviderPlayerGameStat.builder()
                .providerGame(game)
                .lecPlayer(player)
                .externalPlayerId("caps")
                .sourceNickname("Caps")
                .sourceTeamName("G2 Esports")
                .sourceRole(PlayerRole.MID)
                .sourceChampion("Azir")
                .sourceFingerprint("current")
                .rawParticipated(false)
                .correctedParticipated(true)
                .fantasyScore(25.0)
                .overridden(true)
                .build());

        assertThat(repository.findAllByOrderByProviderGamePlayedAtAsc())
                .singleElement()
                .extracting(ProviderPlayerGameStat::getCorrectedParticipated)
                .isEqualTo(true);
    }
}
