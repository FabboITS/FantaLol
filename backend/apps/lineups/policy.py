"""Politiche di modifica delle formazioni (generalizzazione di ``LineupWindow``).

* ``FixedWeeklyWindow``: finestra settimanale fissa (default LEC: mar 00:00 – gio 23:59:59 Europe/Rome,
  effettiva dal venerdì 00:00) — riproduce esattamente il comportamento Java.
* ``LockBeforeFirstMatch``: la formazione della giornata è modificabile fino a ``lock_minutes`` prima
  della prima serie della giornata; le modifiche successive valgono dalla giornata seguente.

Tutti gli istanti sono in UTC; il fuso della competizione serve solo a calcolare le finestre.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

DAY_NAMES = {
    1: "lunedì",
    2: "martedì",
    3: "mercoledì",
    4: "giovedì",
    5: "venerdì",
    6: "sabato",
    7: "domenica",
}


@dataclass(frozen=True)
class WindowStatus:
    editable: bool
    next_effective_at: datetime
    reason: str
    lock_at: datetime | None = None
    target_matchday_id: int | None = None


@dataclass(frozen=True)
class MatchdayWindow:
    starts_at: datetime
    ends_at: datetime
    first_match_at: datetime | None = None
    matchday_id: int | None = None


def _midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=zone)


class FixedWeeklyWindow:
    def __init__(
        self, open_day: int = 2, close_day: int = 4, effective_day: int = 5, timezone: str = "Europe/Rome"
    ):
        self.open_day = open_day
        self.close_day = close_day
        self.effective_day = effective_day
        self.zone = ZoneInfo(timezone or "Europe/Rome")

    def is_open_day(self, iso_weekday: int) -> bool:
        if self.open_day <= self.close_day:
            return self.open_day <= iso_weekday <= self.close_day
        return iso_weekday >= self.open_day or iso_weekday <= self.close_day

    def next_effective_at(self, now: datetime) -> datetime:
        local = now.astimezone(self.zone)
        days_ahead = (self.effective_day - local.isoweekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return _midnight(local.date() + timedelta(days=days_ahead), self.zone).astimezone(ZoneInfo("UTC"))

    def status(self, now: datetime, windows: Sequence[MatchdayWindow] = ()) -> WindowStatus:
        local = now.astimezone(self.zone)
        editable = self.is_open_day(local.isoweekday())
        span = f"da {DAY_NAMES[self.open_day]} a {DAY_NAMES[self.close_day]}"
        reason = f"Le modifiche sono aperte {span}." if editable else f"Le modifiche sono disponibili {span}."
        return WindowStatus(editable, self.next_effective_at(now), reason)

    @property
    def closed_message(self) -> str:
        return (
            f"Le formazioni si possono modificare da {DAY_NAMES[self.open_day]} a {DAY_NAMES[self.close_day]}"
        )


class LockBeforeFirstMatch:
    def __init__(self, lock_minutes: int = 60, timezone: str = "UTC"):
        self.lock = timedelta(minutes=lock_minutes)
        self.lock_minutes = lock_minutes
        self.zone = ZoneInfo(timezone or "UTC")

    def lock_at(self, window: MatchdayWindow) -> datetime | None:
        return window.first_match_at - self.lock if window.first_match_at else None

    def status(self, now: datetime, windows: Sequence[MatchdayWindow] = ()) -> WindowStatus:
        candidates = sorted((w for w in windows if w.ends_at > now), key=lambda w: w.starts_at)
        for index, window in enumerate(candidates):
            lock = self.lock_at(window)
            if lock is None or now < lock:
                effective = now if index == 0 else window.starts_at
                when = lock.astimezone(self.zone).strftime("%d/%m %H:%M") if lock else None
                reason = (
                    f"Modifiche aperte fino a {when} ({self.lock_minutes} minuti prima della prima serie)."
                    if when
                    else "Modifiche aperte: nessuna serie ancora in programma per la giornata."
                )
                if index > 0:
                    reason = (
                        "La giornata in corso è bloccata: le modifiche varranno dalla giornata successiva. "
                        + reason
                    )
                return WindowStatus(True, effective, reason, lock, window.matchday_id)
        effective = candidates[-1].ends_at if candidates else now
        return WindowStatus(
            True,
            effective,
            "Nessuna giornata modificabile in programma: le modifiche varranno dalla prossima giornata.",
        )

    @property
    def closed_message(self) -> str:  # pragma: no cover - la strategia è sempre modificabile
        return "Formazione bloccata"


def weekly_windows(
    now: datetime, timezone: str, weeks_before: int = 1, weeks_after: int = 6
) -> list[MatchdayWindow]:
    """Settimane lunedì 00:00 → lunedì 00:00 nel fuso della competizione (fallback senza giornate)."""
    zone = ZoneInfo(timezone or "UTC")
    local = now.astimezone(zone)
    monday = local.date() - timedelta(days=local.isoweekday() - 1)
    windows = []
    for offset in range(-weeks_before, weeks_after + 1):
        start = _midnight(monday + timedelta(weeks=offset), zone)
        end = _midnight(monday + timedelta(weeks=offset + 1), zone)
        windows.append(MatchdayWindow(start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))))
    return windows


def build_policy(policy, default_timezone: str):
    """Istanzia la strategia a partire dal modello ``LineupPolicy``."""
    timezone = policy.timezone or default_timezone
    if policy.strategy == "FIXED_WEEKLY_WINDOW":
        return FixedWeeklyWindow(policy.open_day, policy.close_day, policy.effective_day, timezone)
    return LockBeforeFirstMatch(policy.lock_minutes, timezone)
