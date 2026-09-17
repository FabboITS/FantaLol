"""Finestra di modifica formazione: martedì 00:00 -> giovedì 23:59:59.

Porting di `lineup/LineupWindow`. Le modifiche confermate in finestra diventano
effettive dal venerdì successivo alle 00:00 (`Europe/Rome`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings

EDITABLE_REASON = "Le modifiche sono aperte da martedì a giovedì."
LOCKED_REASON = "Le modifiche sono disponibili da martedì a giovedì."

TUESDAY, THURSDAY, FRIDAY = 1, 3, 4  # weekday() 0=lunedì


@dataclass(frozen=True)
class WindowStatus:
    editable: bool
    next_effective_at: datetime
    reason: str


def zone():
    return settings.LINEUP_TIMEZONE


def next_effective_at(now: datetime) -> datetime:
    """Prossimo venerdì 00:00 locale (quello dopo, se oggi è già venerdì)."""
    local_now = now.astimezone(zone())
    days_ahead = (FRIDAY - local_now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    friday = (local_now + timedelta(days=days_ahead)).date()
    return datetime(friday.year, friday.month, friday.day, tzinfo=zone())


def status(now: datetime) -> WindowStatus:
    local_now = now.astimezone(zone())
    editable = TUESDAY <= local_now.weekday() <= THURSDAY
    return WindowStatus(
        editable=editable,
        next_effective_at=next_effective_at(now),
        reason=EDITABLE_REASON if editable else LOCKED_REASON,
    )
