"""Bonus specifici del torneo Worlds.

Modulo volutamente isolato: la formula per-ruolo di `scoring/` resta condivisa
con LEC/LPL/LCK e non viene toccata da quanto succede qui.

Tre bonus, tutti configurabili:
 - **MVP serie** (`WorldsLeague.mvp_bonus`, default +3): il player indicato come
   MVP da Leaguepedia porta il bonus al team che lo schierava in quella fase;
 - **Avanzamento di fase** (`WorldsStage.advancement_bonus`, default +2): ogni
   titolare la cui squadra pro accede alla fase successiva porta il bonus;
 - **Vittoria serie** (`WorldsLeague.series_win_bonus`, default +1): ogni serie
   vinta dalla squadra pro di un titolare porta il bonus.
"""
from __future__ import annotations

from dataclasses import dataclass

from ingest.models import Game, Match


@dataclass(frozen=True)
class BonusBreakdown:
    """Dettaglio dei bonus di una fase, così da poterli mostrare in UI."""

    mvp: float = 0.0
    advancement: float = 0.0
    series_win: float = 0.0

    @property
    def total(self) -> float:
        return self.mvp + self.advancement + self.series_win

    def as_dict(self) -> dict:
        return {"mvp": self.mvp, "advancement": self.advancement,
                "seriesWin": self.series_win, "total": self.total}


def _pro_team_names(players) -> dict[int, str]:
    """Nome della squadra pro di ciascun titolare (per il match sui risultati)."""
    return {player.id: (player.team.leaguepedia_name or player.team.nome) for player in players}


def mvp_bonus(stage, players, *, amount: float) -> float:
    """+`amount` per ogni game della fase il cui MVP è un titolare schierato."""
    if amount == 0:
        return 0.0
    player_ids = {player.id for player in players}
    if not player_ids:
        return 0.0
    hits = (Game.objects
            .filter(match__worlds_stage=stage, mvp_player_id__in=player_ids)
            .count())
    return hits * amount


def series_win_bonus(stage, players, *, amount: float) -> float:
    """+`amount` per ogni serie della fase vinta dalla squadra pro di un titolare."""
    if amount == 0:
        return 0.0
    team_names = {name.casefold() for name in _pro_team_names(players).values() if name}
    if not team_names:
        return 0.0
    wins = 0
    for match in Match.objects.filter(worlds_stage=stage).exclude(winner_name__isnull=True):
        if (match.winner_name or "").casefold() in team_names:
            wins += 1
    return wins * amount


def _teams_in_stage(stage) -> set[str]:
    names: set[str] = set()
    for match in Match.objects.filter(worlds_stage=stage):
        for opponent in match.opponents or ():
            if opponent:
                names.add(opponent.casefold())
    return names


def advancement_bonus(stage, players, *, amount: float) -> float:
    """+`amount` per ogni titolare la cui squadra pro compare nella fase successiva."""
    if amount == 0:
        return 0.0
    next_stage = (stage.edition.stages
                  .filter(ordine__gt=stage.ordine)
                  .order_by("ordine")
                  .first())
    if next_stage is None:
        # Ultima fase del torneo: non c'è alcun avanzamento da premiare.
        return 0.0
    advancing = _teams_in_stage(next_stage)
    if not advancing:
        return 0.0
    hits = sum(1 for name in _pro_team_names(players).values()
               if name and name.casefold() in advancing)
    return hits * amount


def compute(stage, players, *, league) -> BonusBreakdown:
    """Bonus complessivi di una fase per una formazione."""
    players = list(players)
    return BonusBreakdown(
        mvp=mvp_bonus(stage, players, amount=league.mvp_bonus),
        advancement=advancement_bonus(stage, players, amount=stage.advancement_bonus),
        series_win=series_win_bonus(stage, players, amount=league.series_win_bonus),
    )
