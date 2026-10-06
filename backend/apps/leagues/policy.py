"""Generalizzazione di ``RosterPolicy``: la soglia dipende dal numero di team reali dell'edizione (T)."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TEAM_COUNT = 10
WORLDS_ROSTER_SIZE = 8
WORLDS_STARTERS = 5
WORLDS_BENCH = 3
WORLDS_MIN_PARTICIPANTS = 2
WORLDS_MAX_PARTICIPANTS = 50


@dataclass(frozen=True)
class Limits:
    max_roster_size: int
    max_per_role: int | None


def limits_for(participants: int, team_count: int) -> Limits:
    """Rosa da 10 (2 per ruolo) se partecipanti ≤ floor(T/2), altrimenti rosa da 5 (1 per ruolo)."""
    return Limits(10, 2) if participants <= team_count // 2 else Limits(5, 1)


def edition_team_count(edition) -> int:
    from apps.esports.models import EditionRoster

    count = (
        EditionRoster.objects.filter(edition=edition, active_to__isnull=True)
        .values("team_id")
        .distinct()
        .count()
    )
    return count or DEFAULT_TEAM_COUNT


def participants(league) -> int:
    if league.participant_count is not None:
        return league.participant_count
    return league.fanta_teams.count()


def roster_limits(league) -> Limits:
    if league.is_worlds:
        return Limits(WORLDS_ROSTER_SIZE, None)
    return limits_for(participants(league), edition_team_count(league.edition))


def max_participants(league) -> int:
    if league.is_worlds:
        return int(league.settings.get("max_participants", WORLDS_MAX_PARTICIPANTS))
    return edition_team_count(league.edition)


def fixed_roster_threshold(league) -> int:
    return edition_team_count(league.edition) // 2 + 1


def is_fixed_roster(league) -> bool:
    """Leghe regionali con rosa da 5: la formazione coincide con la rosa."""
    if league.is_worlds or league.participant_count is None:
        return False
    return league.participant_count >= fixed_roster_threshold(league)
