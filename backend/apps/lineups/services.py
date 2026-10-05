"""Storico dei titolari (porting di ``EffectiveLineupService`` e ``LineupBackfillService``)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Min

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException
from apps.common.utils import ROLE_VALUES, now
from apps.esports.models import EsportsMatch, MatchStatus, ProPlayer
from apps.leagues import policy as roster_policy
from apps.leagues.models import FantaTeam, League
from apps.leagues.services import assert_owner, edition_roster_map

from .models import EffectiveLineupPeriod, LineupPeriodOrigin
from .policy import FixedWeeklyWindow, MatchdayWindow, WindowStatus, build_policy, weekly_windows


# --------------------------------------------------------------------------- finestre
def league_windows(league: League) -> list[MatchdayWindow]:
    """Finestre delle giornate (della lega se esistono, altrimenti settimane) con la prima serie."""
    from apps.matchdays.models import Matchday

    edition = league.edition
    days = list(
        Matchday.objects.filter(league=league, starts_at__isnull=False, ends_at__isnull=False).order_by(
            "starts_at"
        )
    )
    if days:
        raw = [(d.starts_at, d.ends_at, d.id) for d in days]
    else:
        raw = [(w.starts_at, w.ends_at, None) for w in weekly_windows(now(), edition.competition.timezone)]
    windows = []
    for start, end, matchday_id in raw:
        first = (
            EsportsMatch.objects.filter(edition=edition, begin_at__gte=start, begin_at__lt=end)
            .exclude(status=MatchStatus.CANCELED)
            .aggregate(first=Min("begin_at"))["first"]
        )
        windows.append(MatchdayWindow(start, end, first, matchday_id))
    return windows


def league_policy(league: League):
    edition = league.edition
    return build_policy(edition.get_lineup_policy(), edition.competition.timezone)


def window_status(league: League, instant=None) -> WindowStatus:
    instant = instant or now()
    strategy = league_policy(league)
    if isinstance(strategy, FixedWeeklyWindow):
        return strategy.status(instant)
    return strategy.status(instant, league_windows(league))


def closed_message(league: League) -> str:
    strategy = league_policy(league)
    return getattr(strategy, "closed_message", "Formazione bloccata")


# --------------------------------------------------------------------------- consultazione
def active_players_at(team_id: int, instant) -> list[ProPlayer]:
    periods = (
        EffectiveLineupPeriod.objects.select_related("player")
        .filter(fanta_team_id=team_id, effective_from__lte=instant)
        .exclude(effective_until__lte=instant)
    )
    return [p.player for p in periods]


def active_period_at(team_id: int, role: str, instant) -> EffectiveLineupPeriod | None:
    return (
        EffectiveLineupPeriod.objects.filter(fanta_team_id=team_id, role=role, effective_from__lte=instant)
        .exclude(effective_until__lte=instant)
        .first()
    )


def scheduled_players(team_id: int) -> list[ProPlayer]:
    periods = EffectiveLineupPeriod.objects.select_related("player").filter(
        fanta_team_id=team_id, effective_until__isnull=True
    )
    return [p.player for p in periods]


# --------------------------------------------------------------------------- validazioni
def player_roles(team: FantaTeam, players: list[ProPlayer]) -> dict[int, str]:
    roster = edition_roster_map(team.league.edition_id, [p.id for p in players])
    return {p.id: roster[p.id].role for p in players if p.id in roster}


def validate_five_roles(team: FantaTeam, players: list[ProPlayer]) -> dict[int, str]:
    roles = player_roles(team, players)
    ids = {p.id for p in players}
    if (
        len(players) != len(ROLE_VALUES)
        or len(ids) != len(ROLE_VALUES)
        or sorted(roles.get(p.id, "") for p in players) != sorted(ROLE_VALUES)
    ):
        raise BusinessRuleException("La formazione deve contenere esattamente un player per ruolo")
    return roles


# --------------------------------------------------------------------------- scritture
@transaction.atomic
def schedule(user, team_id: int, players: list[ProPlayer]) -> WindowStatus:
    team = _team(team_id)
    assert_owner(team, user)
    league = team.league
    if roster_policy.is_fixed_roster(league):
        raise BusinessRuleException(
            f"Nelle leghe con almeno {roster_policy.fixed_roster_threshold(league)} squadre la formazione "
            "coincide automaticamente con la rosa"
        )
    status = window_status(league)
    if not status.editable:
        raise BusinessRuleException(closed_message(league))
    roles = validate_five_roles(team, players)
    replace_open_periods(team, players, roles, status.next_effective_at, LineupPeriodOrigin.USER)
    return status


@transaction.atomic
def schedule_confirmed(user, team_id: int, players: list[ProPlayer]) -> None:
    team = _team(team_id)
    assert_owner(team, user)
    status = window_status(team.league)
    if not status.editable:
        raise BusinessRuleException(closed_message(team.league))
    roles = validate_five_roles(team, players)
    backfill_from = backfill_instant(team.league)
    if not EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_from=backfill_from).exists():
        create_historical_periods(team, players, roles, backfill_from)
    else:
        replace_open_periods(team, players, roles, status.next_effective_at, LineupPeriodOrigin.USER)


def backfill_instant(league: League):
    return league.edition.starts_at


def create_backfill_periods(team: FantaTeam, players: list[ProPlayer], effective_from) -> None:
    if EffectiveLineupPeriod.objects.filter(fanta_team=team).exists():
        return
    roles = validate_five_roles(team, players)
    EffectiveLineupPeriod.objects.bulk_create(
        _new_periods(team, players, roles, effective_from, LineupPeriodOrigin.BACKFILL)
    )


def ensure_historical_backfill(team: FantaTeam, players: list[ProPlayer], effective_from) -> None:
    if not EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_from=effective_from).exists():
        create_historical_periods(team, players, validate_five_roles(team, players), effective_from)


def create_historical_periods(
    team: FantaTeam, players: list[ProPlayer], roles: dict[int, str], effective_from
) -> None:
    open_periods = EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_until__isnull=True)
    future = [p.effective_from for p in open_periods if p.effective_from > effective_from]
    first_future_change = min(future) if future else None
    EffectiveLineupPeriod.objects.bulk_create(
        [
            EffectiveLineupPeriod(
                fanta_team=team,
                role=roles[p.id],
                player=p,
                effective_from=effective_from,
                effective_until=first_future_change,
                origin=LineupPeriodOrigin.BACKFILL,
            )
            for p in players
        ]
    )


def replace_open_periods(
    team: FantaTeam, players: list[ProPlayer], roles: dict[int, str], effective_from, origin: str
) -> None:
    open_periods = list(EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_until__isnull=True))
    pending = [p for p in open_periods if p.effective_from >= effective_from]
    if pending:
        EffectiveLineupPeriod.objects.filter(pk__in=[p.pk for p in pending]).delete()
    for period in open_periods:
        if period.effective_from < effective_from:
            period.effective_until = effective_from
            period.save(update_fields=["effective_until"])
    EffectiveLineupPeriod.objects.bulk_create(_new_periods(team, players, roles, effective_from, origin))


def _new_periods(team, players, roles, effective_from, origin):
    return [
        EffectiveLineupPeriod(
            fanta_team=team, role=roles[p.id], player=p, effective_from=effective_from, origin=origin
        )
        for p in players
    ]


def ensure_fixed_roster_periods(team: FantaTeam) -> None:
    """Nelle leghe a rosa fissa (5 player) la formazione coincide con la rosa: crea lo storico."""
    league = team.league
    if league.is_worlds or not roster_policy.is_fixed_roster(league):
        return
    players = [e.player for e in team.rosa.select_related("player")]
    roles = player_roles(team, players)
    if len(players) != 5 or sorted(roles.values()) != sorted(ROLE_VALUES):
        return
    current = {
        p.player_id
        for p in EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_until__isnull=True)
    }
    if current == {p.id for p in players}:
        return
    if not EffectiveLineupPeriod.objects.filter(fanta_team=team).exists():
        create_backfill_periods(team, players, backfill_instant(league))
    else:
        replace_open_periods(team, players, roles, now(), LineupPeriodOrigin.AUTOMATIC)


def _team(team_id: int) -> FantaTeam:
    team = (
        FantaTeam.objects.select_related("league__edition__competition", "owner").filter(pk=team_id).first()
    )
    if team is None:
        raise ResourceNotFoundException(f"FantaTeam non trovata con id: {team_id}")
    return team


def backfill_all() -> int:
    """Porting di ``LineupBackfillService.backfill``: crea lo storico mancante dei titolari.

    Rose fisse → periodi dalla rosa; leghe con riserve → dall'ultima formazione valida (SUBMITTED o CARRIED).
    Formazioni o rose non valide vengono saltate senza bloccare le altre squadre.
    """
    from apps.matchdays.models import Formation, FormationSource

    created = 0
    for team in FantaTeam.objects.select_related("league__edition").filter(league__ruleset="REGIONAL"):
        effective_from = backfill_instant(team.league)
        players: list[ProPlayer] | None = None
        if roster_policy.is_fixed_roster(team.league):
            candidate = [e.player for e in team.rosa.select_related("player")]
            players = candidate if _valid_lineup(team, candidate) else None
        else:
            formations = Formation.objects.filter(
                fanta_team=team, source__in=[FormationSource.SUBMITTED, FormationSource.CARRIED]
            ).order_by("-matchday__numero")
            for formation in formations:
                candidate = list(formation.titolari.all())
                if _valid_lineup(team, candidate):
                    players = candidate
                    break
        if players is None:
            continue
        if EffectiveLineupPeriod.objects.filter(fanta_team=team).exists():
            if not EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_from=effective_from).exists():
                ensure_historical_backfill(team, players, effective_from)
                created += 1
        else:
            create_backfill_periods(team, players, effective_from)
            created += 1
    return created


def _valid_lineup(team: FantaTeam, players: list[ProPlayer]) -> bool:
    roles = player_roles(team, players)
    return len({p.id for p in players}) == len(ROLE_VALUES) and sorted(roles.values()) == sorted(ROLE_VALUES) \
        and len(players) == len(ROLE_VALUES)
