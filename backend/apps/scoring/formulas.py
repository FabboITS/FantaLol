"""Formule di punteggio (porting 1:1 di ``GameScoreCalculator``, ``RoleScoreWeights`` e
``FantaScoreCalculator`` del backend Java)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from apps.competitions.models import ScoringFormulaVersion

WIN_BONUS = 3.0


@dataclass(frozen=True)
class Weights:
    kills: float
    assists: float
    deaths: float
    cs_per_hundred: float


ROLE_WEIGHTS: dict[str, Weights] = {
    "TOP": Weights(3.00, 2.00, 2.00, 1.25),
    "JUNGLE": Weights(3.00, 2.25, 2.00, 0.70),
    "MID": Weights(3.00, 2.00, 2.00, 1.00),
    "ADC": Weights(3.25, 1.75, 2.25, 1.10),
    "SUPPORT": Weights(2.15, 2.55, 1.75, 0.0),
}


def weights_for(role: str | None) -> Weights:
    if not role:
        raise ValueError("Player role is required")
    try:
        return ROLE_WEIGHTS[role]
    except KeyError:
        raise ValueError(f"Unknown player role: {role}")


def _resource(role: str, cs: int, vision_score: int, weights: Weights) -> float:
    if role == "SUPPORT":
        return vision_score / 50.0
    return (cs / 100.0) * weights.cs_per_hundred


def _weighted_total(role: str, kills: int, deaths: int, assists: int, cs: int, vision_score: int) -> float:
    w = weights_for(role)
    return kills * w.kills + assists * w.assists - deaths * w.deaths + _resource(role, cs, vision_score, w)


def game_score(
    role: str, kills: int, deaths: int, assists: int, cs: int, vision_score: int, win: bool
) -> float:
    """Fantapunti di un singolo game (formula REGIONAL_V1)."""
    return _weighted_total(role, kills, deaths, assists, cs, vision_score) + (WIN_BONUS if win else 0.0)


def average_score(
    role: str, kills: int, deaths: int, assists: int, cs: int, vision_score: int, wins: int, games_played: int
) -> float:
    """Media per game di statistiche aggregate su più game."""
    if games_played <= 0:
        return 0.0
    return (_weighted_total(role, kills, deaths, assists, cs, vision_score) + wins * WIN_BONUS) / games_played


def historical_score(kills: int, deaths: int, assists: int, cs: int, wins: int) -> float:
    """Formula storica (pre Summer 2026): CS solo a centinaia complete, coefficienti unici."""
    return kills * 3.0 + assists * 2.0 - deaths * 2.0 + (cs // 100) + wins * 3.0


def stat_score(
    *,
    formula_version: str,
    role: str,
    kills: int,
    deaths: int,
    assists: int,
    cs: int,
    vision_score: int,
    wins: int,
    games_played: int,
) -> float:
    if formula_version == ScoringFormulaVersion.HISTORICAL:
        return historical_score(kills, deaths, assists, cs, wins)
    return average_score(role, kills, deaths, assists, cs, vision_score, wins, games_played)


def series_score(game_scores: Iterable[float]) -> float:
    """In una serie conta la media delle sole partite giocate dal player."""
    scores = list(game_scores)
    return sum(scores) / len(scores) if scores else 0.0


def matchday_score(series: Iterable[Iterable[float]]) -> float:
    """Più serie nella stessa giornata: i punteggi (medie per serie) si sommano."""
    return sum(series_score(s) for s in series)


def regional_team_score(slot_scores: Iterable[float | None]) -> float:
    """Media aritmetica dei 5 slot attivi: player senza statistiche = 0, divisione comunque per 5."""
    return sum(score or 0.0 for score in slot_scores) / 5.0
