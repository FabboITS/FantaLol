"""Calcolo del fantavoto di game (porting di `scoring/GameScoreCalculator`)."""
from __future__ import annotations

from teams.models import PlayerRole

from .weights import SUPPORT_VISION_DIVISOR, WIN_BONUS, weights_for


def resource_score(role: str, cs: int, vision_score: int) -> float:
    """Contributo "risorsa": CS per le lane/jungle, vision score per il support."""
    if role == PlayerRole.SUPPORT.value:
        return vision_score / SUPPORT_VISION_DIVISOR
    return (cs / 100.0) * weights_for(role).cs_per_hundred


def weighted_total(role: str, kills: int, deaths: int, assists: int, cs: int, vision_score: int) -> float:
    w = weights_for(role)
    return (kills * w.kills
            + assists * w.assists
            - deaths * w.deaths
            + resource_score(role, cs, vision_score))


def game_score(role: str, kills: int, deaths: int, assists: int, cs: int,
               vision_score: int, win: bool) -> float:
    """Fantapunti di una singola partita."""
    return weighted_total(role, kills, deaths, assists, cs, vision_score) + (WIN_BONUS if win else 0.0)


def average_score(role: str, kills: int, deaths: int, assists: int, cs: int,
                  vision_score: int, wins: int, games_played: int) -> float:
    """Media sui game aggregati (equivalente di `calculateAverage`)."""
    if games_played <= 0:
        return 0.0
    total = weighted_total(role, kills, deaths, assists, cs, vision_score) + wins * WIN_BONUS
    return total / games_played


def historical_score(kills: int, deaths: int, assists: int, cs: int, wins: int) -> float:
    """Formula storica pre-Summer 2026 (`FantaScoreCalculator.calculate`)."""
    return kills * 3.0 + assists * 2.0 - deaths * 2.0 + (cs // 100) + wins * 3.0
