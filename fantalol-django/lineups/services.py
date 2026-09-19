"""Gestione formazione effettiva e storico periodi (`EffectiveLineupService`)."""
from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.exceptions import BusinessRuleError
from leagues.models import FantaTeam
from leagues.services import assert_team_owner
from teams.models import ROLE_ORDER, ProPlayer

from . import window
from .models import LineupPeriod, LineupPeriodOrigin

ROLE_COUNT = len(ROLE_ORDER)


def split_backfill_from() -> datetime:
    """Istante d'inizio dello split corrente (storico formazioni)."""
    parsed = parse_datetime(settings.FANTALOL["SPLIT_BACKFILL_FROM"])
    if parsed is None:
        raise BusinessRuleError("SPLIT_BACKFILL_FROM non è una data ISO valida")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, settings.LINEUP_TIMEZONE)
    return parsed


def validate_five_roles(players) -> None:
    """Esattamente un player per ciascuno dei 5 ruoli, senza duplicati."""
    players = list(players)
    ids = {p.id for p in players}
    roles = {p.ruolo for p in players}
    if len(players) != ROLE_COUNT or len(ids) != ROLE_COUNT or len(roles) != ROLE_COUNT:
        raise BusinessRuleError("La formazione deve contenere esattamente un player per ruolo")


def active_players_at(fanta_team_id, played_at) -> set[int]:
    return {
        period.player_id
        for period in LineupPeriod.objects.filter(fanta_team_id=fanta_team_id, valid_from__lte=played_at)
        if period.valid_to is None or period.valid_to > played_at
    }


def active_period_at(fanta_team_id, role: str, played_at) -> LineupPeriod | None:
    """Il periodo che occupava lo slot `role` nell'istante indicato."""
    return (LineupPeriod.objects
            .filter(fanta_team_id=fanta_team_id, role=role, valid_from__lte=played_at)
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gt=played_at))
            .order_by("-valid_from")
            .first())


def scheduled_players(fanta_team_id) -> list[ProPlayer]:
    """Formazione attualmente pianificata (periodi ancora aperti)."""
    periods = (LineupPeriod.objects
               .filter(fanta_team_id=fanta_team_id, valid_to__isnull=True)
               .select_related("player")
               .order_by("role"))
    return [period.player for period in periods]


@transaction.atomic
def schedule(user, fanta_team_id, players, *, now=None) -> list[ProPlayer]:
    """Pianifica la formazione per la prossima finestra (venerdì 00:00)."""
    fanta_team = FantaTeam.objects.select_related("league", "owner").get(pk=fanta_team_id)
    assert_team_owner(user, fanta_team)
    if fanta_team.league.has_fixed_roster:
        raise BusinessRuleError(
            "Nelle leghe con almeno 6 squadre la formazione coincide automaticamente con la rosa")

    now = now or timezone.now()
    state = window.status(now)
    if not state.editable:
        raise BusinessRuleError("Le formazioni si possono modificare da martedì a giovedì")
    validate_five_roles(players)
    _replace_open_periods(fanta_team, players, state.next_effective_at, LineupPeriodOrigin.USER)
    return list(players)


@transaction.atomic
def schedule_confirmed(user, fanta_team_id, players, *, now=None) -> list[ProPlayer]:
    """Conferma formazione: al primo invio dello split crea i periodi storici."""
    fanta_team = FantaTeam.objects.select_related("league", "owner").get(pk=fanta_team_id)
    assert_team_owner(user, fanta_team)
    now = now or timezone.now()
    state = window.status(now)
    if not state.editable:
        raise BusinessRuleError("Le formazioni si possono modificare da martedì a giovedì")
    validate_five_roles(players)
    backfill_from = split_backfill_from()
    if not LineupPeriod.objects.filter(fanta_team=fanta_team, valid_from=backfill_from).exists():
        _create_historical_periods(fanta_team, players, backfill_from)
    else:
        _replace_open_periods(fanta_team, players, state.next_effective_at, LineupPeriodOrigin.USER)
    return list(players)


@transaction.atomic
def ensure_backfill(fanta_team: FantaTeam, players, valid_from) -> None:
    """Crea i periodi iniziali per una squadra che non ne ha ancora."""
    if LineupPeriod.objects.filter(fanta_team=fanta_team).exists():
        return
    validate_five_roles(players)
    _create_periods(fanta_team, players, valid_from, LineupPeriodOrigin.BACKFILL)


def _create_historical_periods(fanta_team: FantaTeam, players, valid_from) -> None:
    open_periods = list(LineupPeriod.objects.filter(fanta_team=fanta_team, valid_to__isnull=True))
    future_changes = [p.valid_from for p in open_periods if p.valid_from > valid_from]
    first_future_change = min(future_changes) if future_changes else None
    LineupPeriod.objects.bulk_create([
        LineupPeriod(
            fanta_team=fanta_team,
            role=player.ruolo,
            player=player,
            valid_from=valid_from,
            valid_to=first_future_change,
            origin=LineupPeriodOrigin.BACKFILL,
        )
        for player in players
    ])


def _replace_open_periods(fanta_team: FantaTeam, players, valid_from, origin) -> None:
    """Chiude i periodi correnti a `valid_from` e apre i nuovi da lì."""
    open_periods = list(LineupPeriod.objects.filter(fanta_team=fanta_team, valid_to__isnull=True))
    pending = [p for p in open_periods if p.valid_from >= valid_from]
    if pending:
        LineupPeriod.objects.filter(pk__in=[p.pk for p in pending]).delete()
    current = [p for p in open_periods if p.valid_from < valid_from]
    for period in current:
        period.close_at(valid_from)
    if current:
        LineupPeriod.objects.bulk_update(current, ["valid_to"])
    _create_periods(fanta_team, players, valid_from, origin)


def _create_periods(fanta_team: FantaTeam, players, valid_from, origin) -> None:
    LineupPeriod.objects.bulk_create([
        LineupPeriod(
            fanta_team=fanta_team,
            role=player.ruolo,
            player=player,
            valid_from=valid_from,
            origin=origin,
        )
        for player in players
    ])
