package com.fantalol.backend.integration.lec;

import com.fantalol.backend.integration.pandascore.PandaScoreClient;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.concurrent.atomic.AtomicReference;

@Service
@RequiredArgsConstructor
public class LecLiveDataService {
    private final PandaScoreClient pandaScoreClient;
    private final OracleElixirClient oracleElixirClient;
    private final LecDataParser parser;
    private final LecSyncProperties properties;
    private final AtomicReference<LecDataSnapshot> snapshot = new AtomicReference<>(LecDataSnapshot.empty());

    @Scheduled(cron = "${fantalol.lec.sync-cron:0 15 */6 * * *}")
    public LecDataSnapshot synchronize() {
        try {
            LecDataSnapshot fresh = parser.parse(
                    pandaScoreClient.getTournamentMatches(properties.tournamentId()),
                    oracleElixirClient.download(),
                    properties.league(),
                    properties.split()
            );
            snapshot.set(fresh);
            return fresh;
        } catch (RuntimeException exception) {
            LecDataSnapshot previous = snapshot.get();
            LecDataSnapshot stale = new LecDataSnapshot(
                    previous.lastUpdatedAt() == null ? "awaiting-data" : "stale",
                    previous.lastUpdatedAt(),
                    previous.provisional(),
                    previous.standings(),
                    previous.performances(),
                    previous.matches()
            );
            snapshot.set(stale);
            return stale;
        }
    }

    public LecDataSnapshot current() {
        return snapshot.get();
    }
}
