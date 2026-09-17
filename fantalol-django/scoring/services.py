"""Punteggi cumulativi e classifiche (porting di `CumulativeScoringService`).

- Punteggio player  = media dei fantavoti dei game giocati nello split.
- Punteggio team    = media dei 5 slot di ruolo, dove ogni game viene
  attribuito al titolare **storicamente** schierato in quello slot
  (`lineups.LineupPeriod`), non al titolare attuale.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.conf import settings
from django.db.models import Max

from core.exceptions import ResourceNotFound
from ingest.models import GamePlayerStat
from leagues.models import FantaTeam
from lineups.models import LineupPeriod
from teams.models import ROLE_ORDER

LEAGUEPEDIA_ATTRIBUTION = settings.LEAGUEPEDIA["ATTRIBUTION"]


def observations(competition: str | None = None, *, worlds_only: bool = False):
    """Box score utilizzabili: game valorizzati e player effettivamente in campo."""
    queryset = (GamePlayerStat.objects
                .select_related("player", "game", "game__match")
                .filter(game__played_at__isnull=False))
    if competition:
        queryset = queryset.filter(player__competition=competition)
    if worlds_only:
        queryset = queryset.exclude(game__match__worlds_stage__isnull=True)
    return [stat for stat in queryset.order_by("game__played_at", "id") if stat.participated]


# --------------------------------------------------------------------------
# Punteggi player
# --------------------------------------------------------------------------
def player_scores(competition: str | None = None) -> list[dict]:
    grouped: dict[int, list[GamePlayerStat]] = defaultdict(list)
    for stat in observations(competition):
        grouped[stat.player_id].append(stat)
    scores = [_player_score(stats) for stats in grouped.values()]
    scores.sort(key=lambda item: (-(item["average"] or 0.0), item["nickname"]))
    return scores


def player_score(player_id) -> dict:
    stats = [s for s in observations() if s.player_id == int(player_id)]
    if not stats:
        raise ResourceNotFound(f"Nessuna statistica disponibile per il player con id: {player_id}")
    return _player_score(stats)


def _player_score(stats: list[GamePlayerStat]) -> dict:
    player = stats[0].player
    average = sum(s.fantasy_score for s in stats) / len(stats)
    return {
        "playerId": player.id,
        "nickname": player.nickname,
        "role": player.ruolo,
        "gamesPlayed": len(stats),
        "average": average,
        "status": "available",
    }


# --------------------------------------------------------------------------
# Punteggi FantaTeam
# --------------------------------------------------------------------------
@dataclass
class _SlotAccumulator:
    scores: list[float] = field(default_factory=list)
    players: list[str] = field(default_factory=list)

    def add(self, stat: GamePlayerStat) -> None:
        self.scores.append(stat.fantasy_score)
        if stat.player.nickname not in self.players:
            self.players.append(stat.player.nickname)

    @property
    def total(self) -> float:
        return sum(self.scores)

    def to_payload(self, role: str) -> dict:
        if not self.scores:
            return {"role": role, "gamesPlayed": 0, "average": None,
                    "contributingPlayers": [], "status": "awaiting-data"}
        return {
            "role": role,
            "gamesPlayed": len(self.scores),
            "average": self.total / len(self.scores),
            "contributingPlayers": list(self.players),
            "status": "available",
        }


def _score_teams(teams: list[FantaTeam]) -> list[dict]:
    teams_by_id = {team.id: team for team in teams}
    slots: dict[int, dict[str, _SlotAccumulator]] = {
        team.id: {role.value: _SlotAccumulator() for role in ROLE_ORDER} for team in teams
    }
    periods_by_player: dict[int, list[LineupPeriod]] = defaultdict(list)
    for period in LineupPeriod.objects.filter(fanta_team_id__in=teams_by_id):
        periods_by_player[period.player_id].append(period)

    for stat in observations():
        played_at = stat.game.played_at
        for period in periods_by_player.get(stat.player_id, ()):
            if period.fanta_team_id in teams_by_id and period.active_at(played_at):
                slots[period.fanta_team_id][period.role].add(stat)

    return [_team_payload(team, slots[team.id]) for team in teams]


def _team_payload(team: FantaTeam, slots: dict[str, _SlotAccumulator]) -> dict:
    projections = [slots[role.value].to_payload(role.value) for role in ROLE_ORDER]
    provisional = any(slot["gamesPlayed"] == 0 for slot in projections)
    overall_total = None if provisional else sum(acc.total for acc in slots.values())
    return {
        "fantasyTeamId": team.id,
        "teamName": team.nome,
        "slots": projections,
        "overallTotal": overall_total,
        "provisional": provisional,
    }


def team_score(fanta_team_id) -> dict:
    team = FantaTeam.objects.filter(pk=fanta_team_id).first()
    if team is None:
        raise ResourceNotFound(f"FantaTeam non trovata con id: {fanta_team_id}")
    return _score_teams([team])[0]


def league_ranking(league_id) -> list[dict]:
    teams = list(FantaTeam.objects.filter(league_id=league_id).order_by("id"))
    if not teams:
        return []
    scored = _score_teams(teams)
    scored.sort(key=lambda item: (item["overallTotal"] is None,
                                  -(item["overallTotal"] or 0.0),
                                  item["teamName"]))
    return scored


# --------------------------------------------------------------------------
# Envelope con freschezza dei dati (ex `CumulativeDataFreshnessService`)
# --------------------------------------------------------------------------
def last_updated_at():
    return GamePlayerStat.objects.aggregate(value=Max("game__match__leaguepedia_synced_at"))["value"]


def envelope(items, *, provisional: bool = False) -> dict:
    return {
        "status": "available" if items else "awaiting-data",
        "lastUpdatedAt": last_updated_at(),
        "provisional": provisional,
        "items": items,
        "attribution": LEAGUEPEDIA_ATTRIBUTION,
    }


def player_scores_response(competition: str | None = None) -> dict:
    return envelope(player_scores(competition))


def league_ranking_response(league_id) -> dict:
    items = league_ranking(league_id)
    return envelope(items, provisional=any(item["provisional"] for item in items))


# --------------------------------------------------------------------------
# Ricalcolo su nuovi dati di ingest
# --------------------------------------------------------------------------
def recompute_scores_for_game(game) -> int:
    """Ricalcola i fantapunti dei box score di un game appena arricchito."""
    stats = list(GamePlayerStat.objects.filter(game=game).select_related("player"))
    for stat in stats:
        stat.recompute_fantasy_score()
    if stats:
        GamePlayerStat.objects.bulk_update(stats, ["fantasy_score"])
    return len(stats)


def recompute_scores_for_match(match) -> int:
    total = 0
    for game in match.games.all():
        total += recompute_scores_for_game(game)
    return total
