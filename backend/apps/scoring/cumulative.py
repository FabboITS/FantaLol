"""Punteggi cumulativi per game (porting 1:1 di ``CumulativeScoringService``)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from apps.common.exceptions import ResourceNotFoundException
from apps.common.utils import ROLE_VALUES
from apps.esports.observations import Observation, observations
from apps.leagues.models import FantaTeam
from apps.lineups.models import EffectiveLineupPeriod


def player_scores(edition_id: int) -> list[dict]:
    grouped: dict[int, list[Observation]] = defaultdict(list)
    for obs in observations(edition_id=edition_id):
        if obs.score is not None:
            grouped[obs.player_id].append(obs)
    result = [_player_score(rows) for rows in grouped.values()]
    result.sort(key=lambda s: (-s["average"], s["nickname"]))
    return result


def player_score(edition_id: int, player_id: int) -> dict:
    rows = [o for o in observations(edition_id=edition_id, player_ids=[player_id]) if o.score is not None]
    if not rows:
        raise ResourceNotFoundException(f"Nessuna statistica disponibile per il player con id: {player_id}")
    return _player_score(rows)


def _player_score(rows: list[Observation]) -> dict:
    first = rows[0]
    return {
        "player_id": first.player_id,
        "nickname": first.nickname,
        "role": first.role,
        "games_played": len(rows),
        "average": sum(o.score for o in rows) / len(rows),
        "status": "available",
    }


@dataclass
class SlotAccumulator:
    scores: list[float] = field(default_factory=list)
    players: dict[str, None] = field(default_factory=dict)

    def add(self, obs: Observation) -> None:
        self.scores.append(obs.score)
        self.players[obs.nickname] = None

    @property
    def total(self) -> float:
        return sum(self.scores)

    def to_score(self, role: str) -> dict:
        if not self.scores:
            return {
                "role": role,
                "games_played": 0,
                "average": None,
                "contributing_players": [],
                "status": "awaiting-data",
            }
        return {
            "role": role,
            "games_played": len(self.scores),
            "average": self.total / len(self.scores),
            "contributing_players": list(self.players),
            "status": "available",
        }


def score_teams(teams: list[FantaTeam], obs_list: list[Observation] | None = None) -> list[dict]:
    if not teams:
        return []
    edition_id = teams[0].league.edition_id
    obs_list = observations(edition_id=edition_id) if obs_list is None else obs_list
    slots = {team.id: {role: SlotAccumulator() for role in ROLE_VALUES} for team in teams}
    periods_by_player: dict[int, list[EffectiveLineupPeriod]] = defaultdict(list)
    for period in EffectiveLineupPeriod.objects.filter(fanta_team_id__in=list(slots)).order_by(
        "fanta_team_id", "effective_from"
    ):
        periods_by_player[period.player_id].append(period)
    for obs in obs_list:
        if obs.score is None or obs.played_at is None:
            continue
        for period in periods_by_player.get(obs.player_id, []):
            if period.active_at(obs.played_at):
                slots[period.fanta_team_id][period.role].add(obs)
    return [_team_score(team, slots[team.id]) for team in teams]


def _team_score(team: FantaTeam, slots: dict[str, SlotAccumulator]) -> dict:
    projections = [slots[role].to_score(role) for role in ROLE_VALUES]
    provisional = any(slot["games_played"] == 0 for slot in projections)
    total = None if provisional else sum(acc.total for acc in slots.values())
    return {
        "fantasy_team_id": team.id,
        "team_name": team.nome,
        "slots": projections,
        "overall_total": total,
        "provisional": provisional,
    }


def team_score(team: FantaTeam) -> dict:
    return score_teams([team])[0]


def league_ranking(league) -> list[dict]:
    teams = list(league.fanta_teams.select_related("league").order_by("id"))
    ranking = score_teams(teams)
    ranking.sort(key=lambda s: (s["overall_total"] is None, -(s["overall_total"] or 0.0), s["team_name"]))
    return ranking
