package com.fantalol.backend.integration.pandascore;

import com.fasterxml.jackson.databind.JsonNode;
import com.fantalol.backend.league.LeagueRepository;
import com.fantalol.backend.matchday.Matchday;
import com.fantalol.backend.matchday.MatchdayRepository;
import com.fantalol.backend.matchday.MatchdayStatus;
import com.fantalol.backend.scoring.*;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.*;
import java.time.temporal.TemporalAdjusters;
import java.util.*;

@Service
@RequiredArgsConstructor
public class SummerScheduleService {
    private final PandaScoreClient client;
    private final PandaScoreProperties properties;
    private final LeagueRepository leagueRepository;
    private final MatchdayRepository matchdayRepository;
    private final OfficialSeriesRepository seriesRepository;
    private final MatchdaySeriesRepository matchdaySeriesRepository;

    @Scheduled(cron = "${fantalol.pandascore.schedule-sync-cron:0 45 3 * * *}", zone = "Europe/Rome")
    public void scheduledSync() {
        if (properties.token() != null && !properties.token().isBlank()
                && properties.summerTournamentIds() != null && !properties.summerTournamentIds().isBlank()) {
            sync();
        }
    }

    @Transactional
    public SummerScheduleSyncResult sync() {
        List<JsonNode> matches = new ArrayList<>();
        for (long tournamentId : tournamentIds()) {
            JsonNode response = client.getTournamentMatches(tournamentId);
            if (response != null && response.isArray()) response.forEach(matches::add);
        }
        matches.sort(Comparator.comparing(this::beginAt, Comparator.nullsLast(Comparator.naturalOrder())));
        Map<LocalDate, Integer> weekNumbers = new TreeMap<>();
        for (JsonNode match : matches) {
            Instant start = beginAt(match);
            if (start != null) weekNumbers.putIfAbsent(monday(start), weekNumbers.size() + 1);
        }

        int createdDays = 0;
        int linkedDays = 0;
        for (JsonNode match : matches) {
            Instant start = beginAt(match);
            if (start == null) continue;
            long externalId = match.path("id").asLong();
            String[] teams = teams(match);
            OfficialSeries series = seriesRepository.findByProviderAndExternalId("PANDASCORE", String.valueOf(externalId))
                    .orElseGet(() -> seriesRepository.save(OfficialSeries.builder()
                            .provider("PANDASCORE").externalId(String.valueOf(externalId)).build()));
            series.setScheduledAt(start);
            series.setTeamOne(teams[0]);
            series.setTeamTwo(teams[1]);
            series.setStage(match.path("tournament").path("name").asText("LEC Summer 2026"));
            series.setCompleted(Set.of("finished", "canceled").contains(match.path("status").asText("")));
            seriesRepository.save(series);

            LocalDate week = monday(start);
            int number = weekNumbers.get(week);
            for (var league : leagueRepository.findAll().stream().filter(l -> l.getParticipantCount() != null).toList()) {
                boolean[] created = {false};
                Matchday day = matchdayRepository.findByLeagueIdAndData(league.getId(), week)
                        .orElseGet(() -> {
                            created[0] = true;
                            return matchdayRepository.save(Matchday.builder()
                                    .league(league).numero(number)
                                    .descrizione("LEC Summer 2026 · Week " + number)
                                    .data(week).status(MatchdayStatus.OPEN).build());
                        });
                if (created[0]) createdDays++;
                if (!matchdaySeriesRepository.existsByMatchdayIdAndSeriesId(day.getId(), series.getId())) {
                    matchdaySeriesRepository.save(MatchdaySeries.builder().matchday(day).series(series).build());
                    linkedDays++;
                }
            }
        }
        return new SummerScheduleSyncResult(Instant.now(), matches.size(), createdDays, linkedDays);
    }

    private List<Long> tournamentIds() {
        if (properties.summerTournamentIds() == null) return List.of();
        return Arrays.stream(properties.summerTournamentIds().split(","))
                .map(String::trim).filter(value -> !value.isBlank()).map(Long::parseLong).toList();
    }

    private Instant beginAt(JsonNode match) {
        String value = match.path("begin_at").asText("");
        if (value.isBlank()) return null;
        try {
            return Instant.parse(value);
        } catch (DateTimeException exception) {
            return OffsetDateTime.parse(value).toInstant();
        }
    }

    private LocalDate monday(Instant instant) {
        return instant.atZone(ZoneId.of("Europe/Rome")).toLocalDate()
                .with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY));
    }

    private String[] teams(JsonNode match) {
        String[] names = {"TBD", "TBD"};
        JsonNode opponents = match.path("opponents");
        for (int i = 0; i < Math.min(2, opponents.size()); i++) {
            names[i] = opponents.get(i).path("opponent").path("name").asText("TBD");
        }
        Arrays.sort(names, String.CASE_INSENSITIVE_ORDER);
        return names;
    }
}
