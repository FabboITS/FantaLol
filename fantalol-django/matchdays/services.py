"""Gestione giornate e formazioni (porting di `MatchdayService`/`FormationService`)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.exceptions import BusinessRuleError, ResourceNotFound
from leagues import services as league_services
from leagues.models import FantaTeam, RosterEntry
from lineups import services as lineup_services
from lineups import window
from teams.models import ProPlayer

from .models import Formation, FormationSource, Matchday, MatchdayStatus, PlayerStat

NUMERO_TITOLARI = 5


def get_matchday_or_404(matchday_id) -> Matchday:
    matchday = Matchday.objects.select_related("league").filter(pk=matchday_id).first()
    if matchday is None:
        raise ResourceNotFound(f"Giornata non trovata con id: {matchday_id}")
    return matchday


@transaction.atomic
def create_matchday(user, league_id, numero: int, descrizione: str | None, data) -> Matchday:
    """Creare la prima giornata avvia la competizione e congela i partecipanti."""
    league = league_services.get_league_for_update(league_id)
    league_services.assert_league_creator_or_admin(user, league)
    if Matchday.objects.filter(league=league, numero=numero).exists():
        raise BusinessRuleError(f"La giornata {numero} esiste già in questa lega")
    if not league.competition_started:
        if league.fanta_teams.count() < 2:
            raise BusinessRuleError("Servono almeno 2 squadre per avviare la competizione")
        league_services.start_competition_and_open_auction(league)
    return Matchday.objects.create(league=league, numero=numero,
                                   descrizione=descrizione, data=data)


@transaction.atomic
def close_matchday(user, matchday_id) -> Matchday:
    matchday = get_matchday_or_404(matchday_id)
    league_services.assert_league_creator_or_admin(user, matchday.league)
    matchday.chiusa = True
    matchday.status = MatchdayStatus.CLOSED
    matchday.save(update_fields=["chiusa", "status"])
    _score_formations(matchday)
    return matchday


@transaction.atomic
def mark_waiting_for_postponed(user, matchday_id) -> Matchday:
    matchday = get_matchday_or_404(matchday_id)
    league_services.assert_league_creator_or_admin(user, matchday.league)
    if matchday.chiusa:
        raise BusinessRuleError("La giornata è già chiusa")
    matchday.status = MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES
    matchday.save(update_fields=["status"])
    return matchday


def _score_formations(matchday: Matchday) -> None:
    stats = {stat.player_id: stat.fantavoto
             for stat in PlayerStat.objects.filter(matchday=matchday)}
    for formation in Formation.objects.filter(matchday=matchday).prefetch_related("titolari"):
        formation.punteggio_totale = sum(stats.get(p.id, 0.0) for p in formation.titolari.all())
        formation.save(update_fields=["punteggio_totale"])


# --------------------------------------------------------------------------
# Formazioni
# --------------------------------------------------------------------------
def _resolve_roster_players(fanta_team: FantaTeam, player_ids: list[int]) -> list[ProPlayer]:
    players: list[ProPlayer] = []
    for player_id in player_ids:
        if not RosterEntry.objects.filter(fanta_team=fanta_team, player_id=player_id).exists():
            raise BusinessRuleError(
                f"Il player con id {player_id} non appartiene alla rosa di questa squadra")
        player = ProPlayer.objects.filter(pk=player_id).first()
        if player is None:
            raise ResourceNotFound(f"Player non trovato con id: {player_id}")
        players.append(player)
    return players


def get_fanta_team(user, fanta_team_id) -> FantaTeam:
    team = league_services.get_fanta_team_or_404(fanta_team_id)
    league_services.assert_team_owner(user, team)
    return team


def lineup_window_status(user, fanta_team_id, *, now=None) -> dict:
    team = get_fanta_team(user, fanta_team_id)
    state = window.status(now or timezone.now())
    return {
        "editable": state.editable and not team.league.has_fixed_roster,
        "nextEffectiveAt": state.next_effective_at,
        "reason": state.reason,
    }


def _player_payload(player: ProPlayer, score: float | None = None) -> dict:
    return {
        "id": player.id,
        "nickname": player.nickname,
        "role": player.ruolo,
        "matchdayScore": score,
        "imageUrl": player.image_url,
    }


def lineup_payload(team: FantaTeam, scheduled, *, now=None) -> dict:
    now = now or timezone.now()
    state = window.status(now)
    effective_ids = lineup_services.active_players_at(team.id, now)
    effective = [p for p in _roster_players(team) if p.id in effective_ids]
    return {
        "players": [_player_payload(p) for p in scheduled],
        "effectivePlayers": [_player_payload(p) for p in effective],
        "editable": state.editable and not team.league.has_fixed_roster,
        "nextEffectiveAt": state.next_effective_at,
    }


def _roster_players(team: FantaTeam) -> list[ProPlayer]:
    return [entry.player for entry in team.rosa.select_related("player").all()]


def find_lineup(user, fanta_team_id, *, now=None) -> dict:
    team = get_fanta_team(user, fanta_team_id)
    scheduled = lineup_services.scheduled_players(team.id)
    if not scheduled and team.league.has_fixed_roster:
        # Leghe da 6+ squadre: la formazione coincide con la rosa.
        scheduled = _roster_players(team)
    return lineup_payload(team, scheduled, now=now)


@transaction.atomic
def schedule_lineup(user, fanta_team_id, player_ids: list[int], *, now=None) -> dict:
    team = get_fanta_team(user, fanta_team_id)
    if team.league.auction_open:
        raise BusinessRuleError("Termina l'asta prima di modificare la formazione")
    if team.league.has_fixed_roster:
        raise BusinessRuleError(
            "Nelle leghe con almeno 6 squadre la formazione coincide automaticamente con la rosa")
    if len(player_ids) != NUMERO_TITOLARI or len(set(player_ids)) != NUMERO_TITOLARI:
        raise BusinessRuleError(f"Devi schierare esattamente {NUMERO_TITOLARI} titolari diversi")
    players = _resolve_roster_players(team, player_ids)
    if len({p.ruolo for p in players}) != NUMERO_TITOLARI:
        raise BusinessRuleError("Devi schierare esattamente un titolare per ruolo")
    lineup_services.schedule(user, team.id, players, now=now)
    return lineup_payload(team, players, now=now)


@transaction.atomic
def confirm_formation(user, fanta_team_id, matchday_id, player_ids: list[int], *, now=None) -> Formation:
    """Conferma la formazione per una giornata e apre lo storico di titolarità."""
    team = get_fanta_team(user, fanta_team_id)
    matchday = get_matchday_or_404(matchday_id)
    if matchday.league_id != team.league_id:
        raise BusinessRuleError("La giornata non appartiene alla lega di questa squadra")
    if matchday.chiusa:
        raise BusinessRuleError("La giornata è già chiusa")

    if team.league.has_fixed_roster:
        players = _roster_players(team)
    else:
        if len(player_ids) != NUMERO_TITOLARI or len(set(player_ids)) != NUMERO_TITOLARI:
            raise BusinessRuleError(f"Devi schierare esattamente {NUMERO_TITOLARI} titolari diversi")
        players = _resolve_roster_players(team, player_ids)

    lineup_services.validate_five_roles(players)
    formation, _ = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
    formation.titolari.set(players)
    formation.source = FormationSource.SUBMITTED
    formation.confirmed = True
    formation.save(update_fields=["source", "confirmed"])
    lineup_services.schedule_confirmed(user, team.id, players, now=now)
    return formation


def formation_payload(formation: Formation, *, scores: dict[int, float] | None = None) -> dict:
    scores = scores or {}
    players = list(formation.titolari.all())
    return {
        "id": formation.id,
        "fantaTeamId": formation.fanta_team_id,
        "matchdayId": formation.matchday_id,
        "titolari": [p.nickname for p in players],
        "players": [_player_payload(p, scores.get(p.id, 0.0)) for p in players],
        "source": formation.source,
        "confirmed": formation.confirmed,
        "punteggioTotale": formation.punteggio_totale,
    }


def formation_history(user, fanta_team_id) -> list[dict]:
    team = get_fanta_team(user, fanta_team_id)
    payloads = []
    for formation in (Formation.objects.filter(fanta_team=team)
                      .select_related("matchday").prefetch_related("titolari")
                      .order_by("matchday__numero")):
        scores = {
            stat.player_id: stat.fantavoto
            for stat in PlayerStat.objects.filter(matchday=formation.matchday)
        }
        payloads.append(formation_payload(formation, scores=scores))
    return payloads


@transaction.atomic
def confirm_all_formations(user, league_id, matchday_id) -> list[dict]:
    """Conferma d'ufficio le formazioni mancanti (funzione admin di lega)."""
    league = league_services.get_league_or_404(league_id)
    league_services.assert_league_creator_or_admin(user, league)
    matchday = get_matchday_or_404(matchday_id)
    if matchday.league_id != league.id:
        raise BusinessRuleError("La giornata non appartiene a questa lega")

    payloads = []
    for team in league.fanta_teams.all():
        formation, created = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
        if created or not formation.confirmed:
            scheduled = lineup_services.scheduled_players(team.id) or _roster_players(team)
            if len(scheduled) >= NUMERO_TITOLARI:
                formation.titolari.set(scheduled[:NUMERO_TITOLARI] if not team.league.has_fixed_roster
                                       else scheduled)
                formation.source = FormationSource.AUTOMATIC
                formation.confirmed = True
            else:
                formation.source = FormationSource.MISSING
            formation.save(update_fields=["source", "confirmed"])
        payloads.append(formation_payload(formation))
    return payloads
