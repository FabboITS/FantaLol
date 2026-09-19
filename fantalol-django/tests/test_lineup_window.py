"""Porting di `lineup/LineupWindowTest.java`: finestra martedì -> giovedì."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from lineups import window

ROME = ZoneInfo("Europe/Rome")


def rome(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=ROME)


@pytest.mark.parametrize("moment,editable", [
    ("2026-07-28T00:00:00", True),   # martedì, apertura
    ("2026-07-30T23:59:59", True),   # giovedì, ultimo istante utile
    ("2026-07-27T23:59:59", False),  # lunedì
    ("2026-07-31T00:00:00", False),  # venerdì
    ("2026-03-31T00:00:00", True),   # martedì, ora legale
    ("2026-11-05T23:59:59", True),   # giovedì, ora solare
])
def test_uses_rome_calendar_boundaries_including_dst(moment, editable):
    assert window.status(rome(moment)).editable is editable


@pytest.mark.parametrize("moment,expected", [
    ("2026-07-30T20:00:00", "2026-07-31T00:00:00"),
    ("2026-07-31T00:00:00", "2026-08-07T00:00:00"),
    ("2026-03-31T12:00:00", "2026-04-03T00:00:00"),
])
def test_next_effective_at_is_the_following_friday_midnight(moment, expected):
    assert window.next_effective_at(rome(moment)) == rome(expected)


def test_configured_timezone_changes_the_calendar_boundary(settings):
    monday_2330_utc = datetime(2026, 7, 27, 23, 30, tzinfo=ZoneInfo("UTC"))
    settings.LINEUP_TIMEZONE = ROME
    assert window.status(monday_2330_utc).editable is True  # a Roma è già martedì
    settings.LINEUP_TIMEZONE = ZoneInfo("UTC")
    assert window.status(monday_2330_utc).editable is False


def test_reason_explains_the_window(settings):
    settings.LINEUP_TIMEZONE = ROME
    assert "martedì" in window.status(rome("2026-07-28T10:00:00")).reason
    assert "martedì" in window.status(rome("2026-07-27T10:00:00")).reason
