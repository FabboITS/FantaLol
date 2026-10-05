"""Porting di LineupWindowTest + LineupPolicy LOCK_BEFORE_FIRST_MATCH (Seoul/Shanghai, ora legale)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from apps.lineups.policy import FixedWeeklyWindow, LockBeforeFirstMatch, MatchdayWindow, weekly_windows

ROME = ZoneInfo("Europe/Rome")


def rome(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=ROME)


def test_finestra_lec_usa_il_calendario_di_roma_anche_con_ora_legale():
    window = FixedWeeklyWindow()
    assert window.status(rome("2026-07-28T00:00:00")).editable
    assert window.status(rome("2026-07-30T23:59:59")).editable
    assert not window.status(rome("2026-07-27T23:59:59")).editable
    assert not window.status(rome("2026-07-31T00:00:00")).editable
    assert window.status(rome("2026-03-31T00:00:00")).editable
    assert window.status(rome("2026-11-05T23:59:59")).editable
    assert window.next_effective_at(rome("2026-07-30T20:00:00")) == rome("2026-07-31T00:00:00")
    assert window.next_effective_at(rome("2026-07-31T00:00:00")) == rome("2026-08-07T00:00:00")
    assert window.next_effective_at(rome("2026-03-31T12:00:00")) == rome("2026-04-03T00:00:00")


def test_cambio_ora_legale_ottobre():
    window = FixedWeeklyWindow()
    # 25 ottobre 2026: fine dell'ora legale; il venerdì successivo è alle 00:00 CET (UTC+1).
    assert window.next_effective_at(rome("2026-10-27T10:00:00")) == datetime(2026, 10, 29, 23, tzinfo=UTC)


def test_il_fuso_configurato_cambia_il_confine_del_calendario():
    monday_2330_utc = datetime(2026, 7, 27, 23, 30, tzinfo=UTC)
    assert FixedWeeklyWindow(timezone="Europe/Rome").status(monday_2330_utc).editable
    assert not FixedWeeklyWindow(timezone="UTC").status(monday_2330_utc).editable


def test_messaggi_della_finestra():
    window = FixedWeeklyWindow()
    assert "martedì a giovedì" in window.status(rome("2026-07-28T10:00:00")).reason
    assert window.closed_message == "Le formazioni si possono modificare da martedì a giovedì"


def test_finestra_avvolta_sulla_domenica():
    window = FixedWeeklyWindow(open_day=6, close_day=1, effective_day=2)
    assert window.status(rome("2026-08-01T10:00:00")).editable  # sabato
    assert window.status(rome("2026-08-03T10:00:00")).editable  # lunedì
    assert not window.status(rome("2026-08-05T10:00:00")).editable


def _window(start, days=7, first_offset_hours=None, matchday_id=None):
    first = start + timedelta(hours=first_offset_hours) if first_offset_hours is not None else None
    return MatchdayWindow(start, start + timedelta(days=days), first, matchday_id)


def test_lock_prima_della_prima_serie_seoul():
    seoul = ZoneInfo("Asia/Seoul")
    week1 = datetime(2027, 1, 18, tzinfo=seoul).astimezone(UTC)
    week2 = datetime(2027, 1, 25, tzinfo=seoul).astimezone(UTC)
    windows = [
        _window(week1, first_offset_hours=72 + 17, matchday_id=1),
        _window(week2, first_offset_hours=72 + 17, matchday_id=2),
    ]
    policy = LockBeforeFirstMatch(60, "Asia/Seoul")
    first_match = windows[0].first_match_at
    before = policy.status(first_match - timedelta(minutes=61), windows)
    assert before.editable and before.target_matchday_id == 1
    assert before.next_effective_at == first_match - timedelta(minutes=61)
    assert before.lock_at == first_match - timedelta(hours=1)
    after = policy.status(first_match - timedelta(minutes=59), windows)
    assert after.target_matchday_id == 2
    assert after.next_effective_at == week2
    assert "giornata successiva" in after.reason


def test_lock_shanghai_finestra_futura_e_senza_serie():
    shanghai = ZoneInfo("Asia/Shanghai")
    start = datetime(2027, 3, 1, tzinfo=shanghai).astimezone(UTC)
    windows = [_window(start, matchday_id=7)]
    policy = LockBeforeFirstMatch(60, "Asia/Shanghai")
    status = policy.status(start - timedelta(days=2), windows)
    assert status.editable and status.target_matchday_id == 7 and status.lock_at is None
    assert status.next_effective_at == start - timedelta(days=2)


def test_lock_senza_giornate_e_tutte_bloccate():
    policy = LockBeforeFirstMatch(60)
    now = datetime(2027, 3, 1, tzinfo=UTC)
    assert policy.status(now, []).next_effective_at == now
    locked = [_window(now - timedelta(days=1), days=3, first_offset_hours=1)]
    status = policy.status(now, locked)
    assert status.next_effective_at == locked[0].ends_at and status.target_matchday_id is None


def test_settimane_di_fallback_partono_dal_lunedi_locale():
    windows = weekly_windows(datetime(2026, 8, 5, 12, tzinfo=UTC), "Asia/Seoul", 0, 0)
    assert len(windows) == 1
    assert windows[0].starts_at == datetime(2026, 8, 2, 15, tzinfo=UTC)
    assert windows[0].ends_at - windows[0].starts_at == timedelta(days=7)
