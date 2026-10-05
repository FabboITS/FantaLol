"""Ciclo di vita delle giornate (porting di ``MatchdayService``) + chiusura automatica."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Sum

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException
from apps.common.utils import now
from apps.competitions.models import ScoringFormulaVersion
from apps.esports.models import MatchStatus, ProPlayer
from apps.leagues.models import League
from apps.leagues.services import active_roster_entry, get_league, is_global_admin, start_competition
from apps.scoring.formulas import stat_score
from apps.users.models import User

from . import scoring
from .models import Formation, FormationSource, Matchday, MatchdayStatus, PlayerStat, PlayerStatSource

logger = logging.getLogger(__name__)


def matchday_response(matchday: Matchday) -> dict:
    league = matchday.league
    return {
        "id": matchday.id,
        "league_id": league.id,
        "league_nome": league.nome,
        "numero": matchday.numero,
        "descrizione": matchday.descrizione,
        "data": matchday.data,
        "chiusa": matchday.chiusa,
        "status": matchday.status,
        "auction_locked": not matchday.chiusa and league.auction_open,
        "starts_at": matchday.starts_at,
        "ends_at": matchday.ends_at,
        "provisional": matchday.provisional,
        "stage": matchday.stage.code if matchday.stage_id else None,
    }


def player_stat_response(stat: PlayerStat) -> dict:
    return {
        "id": stat.id,
        "matchday_id": stat.matchday_id,
        "lec_player_id": stat.player_id,
        "lec_player_nickname": stat.player.nickname,
        "kills": stat.kills,
        "morti": stat.morti,
        "assist": stat.assist,
        "cs": stat.cs,
        "vision_score": stat.vision_score,
        "vittoria": stat.vittoria,
        "wins": stat.wins,
        "games_played": stat.games_played,
        "fantavoto": stat.fantavoto,
        "source": stat.source,
        "complete": stat.complete,
    }


def get_matchday(matchday_id: int) -> Matchday:
    matchday = (
        Matchday.objects.select_related("league__edition__competition", "league__admin", "stage")
        .filter(pk=matchday_id)
        .first()
    )
    if matchday is None:
        raise ResourceNotFoundException(f"Giornata non trovata con id: {matchday_id}")
    return matchday


def list_matchdays(league_id: int | None = None) -> list[Matchday]:
    qs = Matchday.objects.select_related("league__admin", "stage").order_by("league_id", "numero")
    if league_id is not None:
        qs = qs.filter(league_id=league_id)
    return list(qs)


def _assert_league_admin(user: User, league: League) -> None:
    if not is_global_admin(user) and league.admin_id != user.id:
        raise BusinessRuleException("Solo l'admin della lega può gestire questa giornata")


def _assert_auction_closed(matchday: Matchday) -> None:
    if matchday.league.auction_open:
        raise BusinessRuleException("Termina l'asta prima di usare o chiudere la giornata")


def week_window(day: date, timezone: str) -> tuple[datetime, datetime]:
    """Settimana di gioco (lunedì 00:00 → lunedì successivo) nel fuso della competizione."""
    zone = ZoneInfo(timezone)
    monday = day - timedelta(days=day.isoweekday() - 1)
    start = datetime.combine(monday, time.min, tzinfo=zone)
    return start.astimezone(ZoneInfo("UTC")), (start + timedelta(days=7)).astimezone(ZoneInfo("UTC"))


@transaction.atomic
def create(
    user: User,
    *,
    league_id: int,
    numero: int | None,
    descrizione: str | None,
    data: date | None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Matchday:
    league = get_league(league_id)
    _assert_league_admin(user, league)
    if league.is_worlds:
        from apps.worlds.services import generate_matchdays

        first_time = not league.competition_started
        if first_time:
            start_competition(league)
        return generate_matchdays(league)[0]
    if numero is None:
        raise BusinessRuleException("Il numero di giornata è obbligatorio")
    if Matchday.objects.filter(league=league, status=MatchdayStatus.OPEN).exists():
        raise BusinessRuleException("Esiste già una giornata aperta per questa lega")
    if Matchday.objects.filter(league=league, numero=numero).exists():
        raise BusinessRuleException(f"Esiste già una giornata con numero: {numero}")
    if not league.competition_started:
        # Come nel backend Java: la prima giornata congela i partecipanti e apre l'asta.
        league = start_competition(league)
    if starts_at is None or ends_at is None:
        reference = data or now().astimezone(ZoneInfo(league.edition.competition.timezone)).date()
        starts_at, ends_at = week_window(reference, league.edition.competition.timezone)
    matchday = Matchday.objects.create(
        league=league, numero=numero, descrizione=descrizione, data=data, starts_at=starts_at, ends_at=ends_at
    )
    scoring.recompute_player_stats(matchday)
    return matchday


@transaction.atomic
def insert_stats(user: User, matchday_id: int, values: dict) -> PlayerStat:
    matchday = get_matchday(matchday_id)
    if not is_global_admin(user):
        raise BusinessRuleException("Solo l'amministratore globale può inserire le statistiche")
    _assert_auction_closed(matchday)
    if matchday.chiusa:
        raise BusinessRuleException(
            f"La giornata {matchday.numero} è già chiusa: impossibile modificare le statistiche"
        )
    player_id = values["lec_player_id"]
    player = ProPlayer.objects.filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFoundException(f"Player non trovato con id: {player_id}")
    info = active_roster_entry(matchday.league.edition_id, player.id)
    role = info.role if info else "MID"
    vittoria = bool(values.get("vittoria"))
    stat_values = {
        "kills": values.get("kills") or 0,
        "morti": values.get("morti") or 0,
        "assist": values.get("assist") or 0,
        "cs": values.get("cs") or 0,
        "vision_score": values.get("vision_score") or 0,
        "vittoria": vittoria,
        "wins": 1 if vittoria else 0,
        "games_played": 1,
        "series_played": 1,
        "formula_version": ScoringFormulaVersion.REGIONAL_V1,
        "source": PlayerStatSource.MANUAL,
        "complete": True,
    }
    stat_values["fantavoto"] = stat_score(
        formula_version=stat_values["formula_version"],
        role=role,
        kills=stat_values["kills"],
        deaths=stat_values["morti"],
        assists=stat_values["assist"],
        cs=stat_values["cs"],
        vision_score=stat_values["vision_score"],
        wins=stat_values["wins"],
        games_played=1,
    )
    stat, _ = PlayerStat.objects.update_or_create(matchday=matchday, player=player, defaults=stat_values)
    return stat


@transaction.atomic
def close(user: User | None, matchday_id: int) -> Matchday:
    matchday = get_matchday(matchday_id)
    if user is not None:
        _assert_league_admin(user, matchday.league)
    _assert_auction_closed(matchday)
    if matchday.chiusa:
        raise BusinessRuleException(f"La giornata {matchday.numero} è già chiusa")
    scoring.recompute_player_stats(matchday)
    league = matchday.league
    if league.is_worlds:
        from apps.worlds.services import close_matchday as close_worlds

        close_worlds(matchday)
    else:
        _close_regional(matchday)
    matchday.chiusa = True
    matchday.status = MatchdayStatus.CLOSED
    matchday.closed_at = now()
    matchday.provisional = scoring.is_provisional(matchday)
    matchday.save(update_fields=["chiusa", "status", "closed_at", "provisional"])
    refresh_team_points(league)
    return matchday


def _close_regional(matchday: Matchday) -> None:
    from apps.leagues.policy import is_fixed_roster
    from apps.lineups.services import ensure_fixed_roster_periods

    obs_list = scoring.matchday_observations(matchday)
    for team in matchday.league.fanta_teams.all():
        ensure_fixed_roster_periods(team)
        formation, created = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
        if not team.lineup_periods.exists():
            # Mai schierata una formazione: 0 punti (come FormationSource.MISSING nel Java).
            formation.source = FormationSource.MISSING
            formation.punteggio_totale = 0.0
            formation.save()
            continue
        total, slots = scoring.regional_team_matchday_score(team.id, matchday, obs_list)
        if is_fixed_roster(team.league):
            formation.source = FormationSource.AUTOMATIC
        elif created or formation.source == FormationSource.MISSING:
            formation.source = FormationSource.CARRIED
        formation.punteggio_totale = total
        formation.save()
        if not formation.titolari.exists():
            formation.titolari.set([pid for slot in slots.values() for pid in slot["player_ids"]])


def refresh_team_points(league: League) -> None:
    for team in league.fanta_teams.all():
        total = (
            (
                Formation.objects.filter(fanta_team=team, matchday__chiusa=True).aggregate(
                    total=Sum("punteggio_totale")
                )["total"]
            )
            or 0.0
        )
        team.punti = total
        team.save(update_fields=["punti"])


@transaction.atomic
def mark_waiting(user: User | None, matchday_id: int) -> Matchday:
    matchday = get_matchday(matchday_id)
    if user is not None:
        _assert_league_admin(user, matchday.league)
    _assert_auction_closed(matchday)
    if matchday.chiusa:
        raise BusinessRuleException("A closed matchday cannot be moved back to waiting")
    matchday.status = MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES
    matchday.save(update_fields=["status"])
    return matchday


def recompute_for_matches(match_ids) -> int:
    """Dopo un arricchimento Leaguepedia ricalcola le giornate aperte che contengono le serie."""
    from apps.esports.models import EsportsMatch

    count = 0
    for match in EsportsMatch.objects.filter(pk__in=list(match_ids), begin_at__isnull=False):
        days = Matchday.objects.select_related("league__edition").filter(
            league__edition_id=match.edition_id,
            chiusa=False,
            starts_at__lte=match.begin_at,
            ends_at__gt=match.begin_at,
        )
        for matchday in days:
            scoring.recompute_player_stats(matchday)
            count += 1
    return count


def auto_close_matchdays() -> dict:
    """Chiude le giornate concluse con statistiche complete; rinvii → WAITING_FOR_POSTPONED_MATCHES."""
    report = {"closed": 0, "waiting": 0}
    candidates = (
        Matchday.objects.select_related("league__edition")
        .filter(chiusa=False, ends_at__lte=now())
        .exclude(ends_at__isnull=True)
    )
    for matchday in candidates:
        league = matchday.league
        if not league.settings.get("auto_close_matchdays", True) or league.auction_open:
            continue
        matches = list(scoring.window_matches(matchday))
        if not matches:
            continue
        postponed = any(
            m.status in (MatchStatus.POSTPONED, MatchStatus.NOT_STARTED, MatchStatus.RUNNING) for m in matches
        )
        if postponed:
            if matchday.status != MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES:
                mark_waiting(None, matchday.id)
                report["waiting"] += 1
            continue
        if all(m.stats_complete for m in matches if m.status == MatchStatus.FINISHED):
            try:
                close(None, matchday.id)
                report["closed"] += 1
            except BusinessRuleException as error:  # pragma: no cover - log difensivo
                logger.warning("Chiusura automatica giornata %s fallita: %s", matchday.id, error)
    return report
