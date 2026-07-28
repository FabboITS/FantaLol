package com.fantalol.backend.lineup;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

import static org.assertj.core.api.Assertions.assertThat;

class LineupWindowTest {

    @Test
    void usesRomeCalendarBoundariesIncludingDaylightSavingTime() {
        LineupWindow window = new LineupWindow();

        assertThat(window.status(rome("2026-07-28T00:00:00")).editable()).isTrue();
        assertThat(window.status(rome("2026-07-30T23:59:59")).editable()).isTrue();
        assertThat(window.status(rome("2026-07-27T23:59:59")).editable()).isFalse();
        assertThat(window.status(rome("2026-07-31T00:00:00")).editable()).isFalse();
        assertThat(window.status(rome("2026-03-31T00:00:00")).editable()).isTrue();
        assertThat(window.status(rome("2026-11-05T23:59:59")).editable()).isTrue();

        assertThat(window.nextEffectiveAt(rome("2026-07-30T20:00:00")))
                .isEqualTo(rome("2026-07-31T00:00:00"));
        assertThat(window.nextEffectiveAt(rome("2026-07-31T00:00:00")))
                .isEqualTo(rome("2026-08-07T00:00:00"));
        assertThat(window.nextEffectiveAt(rome("2026-03-31T12:00:00")))
                .isEqualTo(rome("2026-04-03T00:00:00"));
    }

    @Test
    void configuredTimezoneChangesTheCalendarBoundary() {
        Instant mondayAt2330Utc = Instant.parse("2026-07-27T23:30:00Z");

        LineupWindow romeWindow = new LineupWindow(ZoneId.of("Europe/Rome"));
        LineupWindow utcWindow = new LineupWindow(ZoneId.of("UTC"));

        assertThat(romeWindow.status(mondayAt2330Utc).editable()).isTrue();
        assertThat(utcWindow.status(mondayAt2330Utc).editable()).isFalse();
    }

    private Instant rome(String dateTime) {
        return LocalDateTime.parse(dateTime).atZone(ZoneId.of("Europe/Rome")).toInstant();
    }
}
