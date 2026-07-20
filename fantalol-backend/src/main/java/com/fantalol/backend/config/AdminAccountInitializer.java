package com.fantalol.backend.config;

import com.fantalol.backend.league.AuctionSessionRepository;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.LeagueRepository;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.matchday.FormationRepository;
import com.fantalol.backend.matchday.MatchdayRepository;
import com.fantalol.backend.matchday.PlayerStatRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AdminAccountInitializer {

    static final String ADMIN_USERNAME = "Natsu_Admin";
    private static final String LEGACY_ADMIN_USERNAME = "admin";
    private static final String ADMIN_EMAIL = "natsu-admin@fantalol.local";
    private static final String ADMIN_PASSWORD_HASH =
            "$2y$12$5Cy4nTyT/1FSRnVVlFjgvuczPqt1Dj/6OtWCMkGTRLzuOyRvsYUTq";

    private final FormationRepository formationRepository;
    private final PlayerStatRepository playerStatRepository;
    private final MatchdayRepository matchdayRepository;
    private final AuctionSessionRepository auctionSessionRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final LeagueRepository leagueRepository;
    private final UserRepository userRepository;

    @Transactional
    public void initialize() {
        if (userRepository.existsByUsername(LEGACY_ADMIN_USERNAME)) {
            deleteLegacyUserData();
        }

        if (!userRepository.existsByUsername(ADMIN_USERNAME)) {
            userRepository.save(User.builder()
                    .username(ADMIN_USERNAME)
                    .email(ADMIN_EMAIL)
                    .password(ADMIN_PASSWORD_HASH)
                    .role(Role.ADMIN)
                    .enabled(true)
                    .build());
        }
    }

    private void deleteLegacyUserData() {
        formationRepository.deleteAll();
        formationRepository.flush();
        playerStatRepository.deleteAllInBatch();
        matchdayRepository.deleteAllInBatch();
        auctionSessionRepository.deleteAllInBatch();
        rosterEntryRepository.deleteAllInBatch();
        fantaTeamRepository.deleteAllInBatch();
        leagueRepository.deleteAllInBatch();
        userRepository.deleteAllInBatch();
        userRepository.flush();
    }
}
