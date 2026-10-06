"""Formazioni per giornata e formazione settimanale (porting di ``FormationService``)."""

from __future__ import annotations

from django.db import transaction

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException
from apps.common.utils import now, role_index
from apps.esports.models import ProPlayer
from apps.leagues import policy as roster_policy
from apps.leagues.models import FantaTeam
from apps.leagues.services import edition_roster_map, get_team, is_global_admin
from apps.lineups import services as lineups
from apps.users.models import User

from .models import Formation, FormationSource, Matchday, PlayerStat

NUMERO_TITOLARI = 5


def fixed_roster_message(team: FantaTeam) -> str:
    threshold = roster_policy.fixed_roster_threshold(team.league)
    return f"Nelle leghe con almeno {threshold} squadre la formazione coincide automaticamente con la rosa"


def _player_rows(team: FantaTeam, players, scores: dict[int, float] | None = None) -> list[dict]:
    roster = edition_roster_map(team.league.edition_id, [p.id for p in players])
    rows = [
        {
            "id": p.id,
            "nickname": p.nickname,
            "role": roster[p.id].role if p.id in roster else None,
            "matchday_score": (scores or {}).get(p.id, 0.0),
        }
        for p in players
    ]
    rows.sort(key=lambda r: role_index(r["role"] or ""))
    return rows


def formation_response(formation: Formation, scores: dict[int, float] | None = None) -> dict:
    team = formation.fanta_team
    titolari = list(formation.titolari.all())
    status = lineups.window_status(team.league)
    fixed = roster_policy.is_fixed_roster(team.league)
    effective = lineups.active_players_at(team.id, now())
    return {
        "id": formation.id,
        "fanta_team_id": team.id,
        "matchday_id": formation.matchday_id,
        "titolari": [p.nickname for p in titolari],
        "players": _player_rows(team, titolari, scores),
        "source": formation.source,
        "confirmed": formation.confirmed,
        "punteggio_totale": formation.punteggio_totale,
        "editable": status.editable and not fixed,
        "next_effective_at": status.next_effective_at,
        "effective_players": [p.nickname for p in effective],
        "capitano_id": formation.capitano_id,
        "vice_capitano_id": formation.vice_capitano_id,
        "bench_order": formation.bench_order,
        "captain_points": formation.captain_points,
        "penalty_points": formation.penalty_points,
        "effective_titolari": formation.effective_titolari,
    }


def lineup_response(team: FantaTeam, selected) -> dict:
    status = lineups.window_status(team.league)
    fixed = roster_policy.is_fixed_roster(team.league)
    effective = lineups.active_players_at(team.id, now())
    return {
        "players": _player_rows(team, selected),
        "effective_players": _player_rows(team, effective),
        "editable": status.editable and not fixed,
        "next_effective_at": status.next_effective_at,
    }


def _verify_can_manage(user: User, team: FantaTeam) -> None:
    if team.owner_id != user.id and not is_global_admin(user):
        raise BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica")


def _matchday(matchday_id: int) -> Matchday:
    matchday = Matchday.objects.select_related("league__edition").filter(pk=matchday_id).first()
    if matchday is None:
        raise ResourceNotFoundException(f"Giornata non trovata con id: {matchday_id}")
    return matchday


def find_by_team_and_matchday(team_id: int, matchday_id: int) -> dict:
    formation = (
        Formation.objects.select_related("fanta_team__league__edition")
        .filter(fanta_team_id=team_id, matchday_id=matchday_id)
        .first()
    )
    if formation is None:
        raise ResourceNotFoundException("Nessuna formazione trovata per la squadra e la giornata indicate")
    return formation_response(formation)


def history(team_id: int) -> list[dict]:
    formations = (
        Formation.objects.select_related("fanta_team__league__edition", "matchday")
        .filter(fanta_team_id=team_id)
        .order_by("matchday__numero")
    )
    result = []
    for formation in formations:
        scores = dict(
            PlayerStat.objects.filter(matchday_id=formation.matchday_id).values_list("player_id", "fantavoto")
        )
        result.append(formation_response(formation, scores))
    return result


def lineup_window(user: User, team_id: int) -> dict:
    team = get_team(team_id)
    _verify_can_manage(user, team)
    status = lineups.window_status(team.league)
    fixed = roster_policy.is_fixed_roster(team.league)
    return {
        "editable": status.editable and not fixed,
        "next_effective_at": status.next_effective_at,
        "reason": status.reason,
        "lock_at": status.lock_at,
        "target_matchday_id": status.target_matchday_id,
    }


def find_lineup(user: User, team_id: int) -> dict:
    team = get_team(team_id)
    _verify_can_manage(user, team)
    if team.league.is_worlds:
        from apps.worlds.services import worlds_lineup_response

        return worlds_lineup_response(team)
    return lineup_response(team, lineups.scheduled_players(team.id))


def _roster_players(team: FantaTeam, player_ids: list[int]) -> list[ProPlayer]:
    owned = set(team.rosa.values_list("player_id", flat=True))
    players = []
    for player_id in player_ids:
        if player_id not in owned:
            raise BusinessRuleException(
                f"Il player con id {player_id} non appartiene alla rosa di questa squadra"
            )
        players.append(ProPlayer.objects.get(pk=player_id))
    return players


def _validate_titolari(team: FantaTeam, titolari_ids: list[int]) -> list[ProPlayer]:
    if len(titolari_ids) != NUMERO_TITOLARI or len(set(titolari_ids)) != NUMERO_TITOLARI:
        raise BusinessRuleException(f"Devi schierare esattamente {NUMERO_TITOLARI} titolari diversi")
    players = _roster_players(team, titolari_ids)
    roles = lineups.player_roles(team, players)
    if len({roles.get(p.id) for p in players}) != NUMERO_TITOLARI:
        raise BusinessRuleException(
            "La formazione deve contenere un player per ruolo: TOP, JUNGLE, MID, ADC e SUPPORT"
        )
    return players


@transaction.atomic
def schedule_lineup(user: User, team_id: int, data: dict) -> dict:
    team = get_team(team_id)
    _verify_can_manage(user, team)
    if team.league.is_worlds:
        from apps.worlds.services import save_lineup

        return save_lineup(user, team, data)
    if team.league.auction_open:
        raise BusinessRuleException("Termina l'asta prima di modificare la formazione")
    if roster_policy.is_fixed_roster(team.league):
        raise BusinessRuleException(fixed_roster_message(team))
    players = _validate_titolari(team, data.get("titolari_ids") or [])
    lineups.schedule(user, team.id, players)
    return lineup_response(team, players)


def _current_roster_or_formation(team: FantaTeam, matchday: Matchday) -> list[ProPlayer]:
    if roster_policy.is_fixed_roster(team.league):
        return [e.player for e in team.rosa.select_related("player")]
    formation = (
        Formation.objects.filter(fanta_team=team, matchday=matchday)
        .exclude(source=FormationSource.MISSING)
        .first()
    )
    if formation is not None and formation.titolari.exists():
        return list(formation.titolari.all())
    return lineups.scheduled_players(team.id)


def _validate_confirmation_window(matchday: Matchday) -> None:
    if matchday.chiusa:
        raise BusinessRuleException("La giornata è chiusa: non puoi confermare la formazione")
    if matchday.league.auction_open:
        raise BusinessRuleException("Termina l'asta prima di confermare la formazione")
    status = lineups.window_status(matchday.league)
    if not status.editable:
        raise BusinessRuleException(
            lineups.closed_message(matchday.league).replace(
                "Le formazioni si possono modificare", "La formazione si può confermare"
            )
        )


@transaction.atomic
def confirm(user: User, team_id: int, matchday_id: int) -> dict:
    team = get_team(team_id)
    _verify_can_manage(user, team)
    matchday = _matchday(matchday_id)
    if matchday.league_id != team.league_id:
        raise BusinessRuleException("La giornata non appartiene alla lega della squadra")
    _validate_confirmation_window(matchday)
    players = _current_roster_or_formation(team, matchday)
    lineups.validate_five_roles(team, players)
    formation, _ = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
    formation.source = FormationSource.SUBMITTED
    formation.confirmed = True
    formation.save()
    formation.titolari.set(players)
    if not team.league.is_worlds:
        lineups.schedule_confirmed(user, team.id, players)
    return formation_response(formation)


@transaction.atomic
def confirm_all(user: User, league_id: int, matchday_id: int) -> int:
    if not is_global_admin(user):
        raise BusinessRuleException("Solo l'ADMIN globale può confermare tutte le squadre")
    matchday = _matchday(matchday_id)
    if matchday.league_id != league_id:
        raise BusinessRuleException("La giornata non appartiene alla lega indicata")
    _validate_confirmation_window(matchday)
    confirmed = 0
    for team in FantaTeam.objects.filter(league_id=league_id).select_related("league__edition", "owner"):
        players = _current_roster_or_formation(team, matchday)
        lineups.validate_five_roles(team, players)
        formation, _ = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
        formation.source = FormationSource.SUBMITTED
        formation.confirmed = True
        formation.save()
        formation.titolari.set(players)
        if not team.league.is_worlds:
            lineups.schedule_confirmed(user, team.id, players)
        confirmed += 1
    return confirmed


@transaction.atomic
def imposta(user: User, team_id: int, matchday_id: int, titolari_ids: list[int]) -> dict:
    team = get_team(team_id)
    _verify_can_manage(user, team)
    matchday = _matchday(matchday_id)
    if matchday.chiusa:
        raise BusinessRuleException(
            f"La giornata {matchday.numero} è chiusa: non puoi modificare la formazione"
        )
    if team.league.auction_open:
        raise BusinessRuleException("Termina l'asta prima di modificare la formazione")
    if roster_policy.is_fixed_roster(team.league):
        raise BusinessRuleException(fixed_roster_message(team))
    players = _validate_titolari(team, titolari_ids)
    formation, _ = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
    formation.source = FormationSource.SUBMITTED
    formation.confirmed = False
    formation.save()
    formation.titolari.set(players)
    if not team.league.is_worlds:
        lineups.schedule(user, team.id, players)
    return formation_response(formation)
