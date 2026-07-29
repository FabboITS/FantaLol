package com.fantalol.backend.lineup;

import com.fantalol.backend.integration.lec.LecSyncProperties;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.TemporalAdjusters;

@Component
public class LineupWindow {

    public static final ZoneId ZONE = ZoneId.of("Europe/Rome");
    private final ZoneId zone;

    public LineupWindow() {
        this(ZONE);
    }

    @Autowired
    public LineupWindow(LecSyncProperties properties) {
        this(properties.timezone());
    }

    LineupWindow(ZoneId zone) {
        this.zone = zone;
    }

    public record Status(boolean editable, Instant nextEffectiveAt, String reason) {
    }

    public Status status(Instant now) {
        ZonedDateTime localNow = now.atZone(zone);
        boolean editable = !localNow.getDayOfWeek().equals(DayOfWeek.MONDAY)
                && localNow.getDayOfWeek().getValue() <= DayOfWeek.THURSDAY.getValue();
        return new Status(editable, nextEffectiveAt(now), editable
                ? "Le modifiche sono aperte da martedì a giovedì."
                : "Le modifiche sono disponibili da martedì a giovedì.");
    }

    public Instant nextEffectiveAt(Instant now) {
        ZonedDateTime localNow = now.atZone(zone);
        LocalDate friday = localNow.toLocalDate().with(TemporalAdjusters.nextOrSame(DayOfWeek.FRIDAY));
        if (localNow.getDayOfWeek() == DayOfWeek.FRIDAY) {
            friday = friday.plusWeeks(1);
        }
        return friday.atStartOfDay(zone).toInstant();
    }
}
