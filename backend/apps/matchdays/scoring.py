"""Aggregazione delle statistiche per giornata e punteggio regionale dei FantaTeam."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from apps.common.utils import ROLE_VALUES
from apps.competitions.models import ScoringFormulaVersion
from apps.esports.models import EsportsMatch, MatchStatus
from apps.esports.observations import Observation, observations
from apps.lineups.models import EffectiveLineupPeriod
from apps.scoring.formulas import matchday_score, regional_team_score

from .models import Matchday, PlayerStat, PlayerStatSource


def window_matches(matchday: Matchday):
    if matchday.starts_at is None or matchday.ends_at is None:
        return EsportsMatch.objects.none()
    return (
        EsportsMatch.objects.filter(
            edition_id=matchday.league.edition_id,
            begin_at__gte=matchday.starts_at,
            begin_at__lt=matchday.ends_at,
        )
        .exclude(status=MatchStatus.CANCELED)
        .order_by("begin_at")
    )


def matchday_observations(matchday: Matchday) -> list[Observation]:
    match_ids = list(window_matches(matchday).values_list("id", flat=True))
    if not match_ids:
        return []
    return observations(match_ids=match_ids)


@dataclass
class PlayerAggregate:
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    cs: int = 0
    vision: int = 0
    wins: int = 0
    games: int = 0
    complete: bool = True
    by_series: dict[int, list[float]] = field(default_factory=lambda: defaultdict(list))

    def add(self, obs: Observation) -> None:
        self.kills += obs.kills
        self.deaths += obs.deaths
        self.assists += obs.assists
        self.cs += obs.cs
        self.vision += obs.vision_score
        self.wins += 1 if obs.win else 0
        self.games += 1
        self.complete = self.complete and obs.complete
        if obs.score is not None:
            self.by_series[obs.match_id].append(obs.score)

    @property
    def score(self) -> float:
        return matchday_score(self.by_series.values())


def aggregate(obs_list: list[Observation]) -> dict[int, PlayerAggregate]:
    result: dict[int, PlayerAggregate] = defaultdict(PlayerAggregate)
    for obs in obs_list:
        result[obs.player_id].add(obs)
    return result


def is_provisional(matchday: Matchday) -> bool:
    matches = list(window_matches(matchday))
    if not matches:
        return True
    return any(m.status != MatchStatus.FINISHED or not m.stats_complete for m in matches)


@transaction.atomic
def recompute_player_stats(matchday: Matchday) -> int:
    """Ricalcola i ``PlayerStat`` automatici della giornata (le righe MANUAL dell'admin non si toccano)."""
    if matchday.chiusa:
        return 0
    aggregates = aggregate(matchday_observations(matchday))
    manual = set(
        PlayerStat.objects.filter(matchday=matchday, source=PlayerStatSource.MANUAL).values_list(
            "player_id", flat=True
        )
    )
    version = matchday.league.edition.scoring_formula_version
    if version == ScoringFormulaVersion.SUMMER_2026_V1:
        version = ScoringFormulaVersion.REGIONAL_V1
    for player_id, agg in aggregates.items():
        if player_id in manual:
            continue
        PlayerStat.objects.update_or_create(
            matchday=matchday,
            player_id=player_id,
            defaults={
                "kills": agg.kills,
                "morti": agg.deaths,
                "assist": agg.assists,
                "cs": agg.cs,
                "vision_score": agg.vision,
                "wins": agg.wins,
                "vittoria": agg.wins > 0,
                "games_played": agg.games,
                "series_played": len(agg.by_series),
                "formula_version": version,
                "fantavoto": agg.score,
                "source": PlayerStatSource.AUTO,
                "complete": agg.complete,
            },
        )
    (
        PlayerStat.objects.filter(matchday=matchday, source=PlayerStatSource.AUTO)
        .exclude(player_id__in=list(aggregates))
        .delete()
    )
    provisional = is_provisional(matchday)
    if matchday.provisional != provisional:
        matchday.provisional = provisional
        matchday.save(update_fields=["provisional"])
    return len(aggregates)


def regional_slot_scores(
    team_id: int, matchday: Matchday, obs_list: list[Observation] | None = None
) -> dict[str, dict]:
    """Per ogni ruolo: punteggio dello slot usando i player titolari al momento di ciascun game."""
    obs_list = matchday_observations(matchday) if obs_list is None else obs_list
    periods = list(EffectiveLineupPeriod.objects.filter(fanta_team_id=team_id).select_related("player"))
    manual = {
        s.player_id: s.fantavoto
        for s in PlayerStat.objects.filter(matchday=matchday, source=PlayerStatSource.MANUAL)
    }
    slots: dict[str, dict] = {}
    for role in ROLE_VALUES:
        role_periods = [p for p in periods if p.role == role]
        by_player: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        nicknames: dict[int, str] = {}
        for obs in obs_list:
            if obs.score is None or obs.played_at is None:
                continue
            for period in role_periods:
                if period.player_id == obs.player_id and period.active_at(obs.played_at):
                    by_player[obs.player_id][obs.match_id].append(obs.score)
                    nicknames[obs.player_id] = obs.nickname
        # Player titolari durante la giornata con statistiche inserite manualmente dall'admin.
        for period in role_periods:
            if period.player_id in manual and _overlaps(period, matchday):
                nicknames[period.player_id] = period.player.nickname
        score = 0.0
        for player_id in nicknames:
            if player_id in manual:
                score += manual[player_id]
            else:
                score += matchday_score(by_player[player_id].values())
        starters = [p.player for p in role_periods if _overlaps(p, matchday)]
        slots[role] = {
            "score": score,
            "players": list(nicknames.values()) or [p.nickname for p in starters[:1]],
            "player_ids": list(nicknames) or [p.id for p in starters[:1]],
        }
    return slots


def _overlaps(period: EffectiveLineupPeriod, matchday: Matchday) -> bool:
    if matchday.starts_at is None or matchday.ends_at is None:
        return period.effective_until is None
    return period.effective_from < matchday.ends_at and (
        period.effective_until is None or period.effective_until > matchday.starts_at
    )


def regional_team_matchday_score(team_id: int, matchday: Matchday, obs_list=None) -> tuple[float, dict]:
    slots = regional_slot_scores(team_id, matchday, obs_list)
    return regional_team_score(slot["score"] for slot in slots.values()), slots
