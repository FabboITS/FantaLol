"""Proiezione delle statistiche per game "effettive" (dato Leaguepedia + eventuale override admin).

È l'equivalente di ``ProviderPlayerGameStat`` del backend Java: ogni osservazione è la prestazione
di un player in un game, con il fantapunteggio calcolato usando il ruolo dell'``EditionRoster``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from django.db.models import QuerySet

from apps.scoring.formulas import game_score

from .models import EditionRoster, EsportsGame, GamePlayerStat, GamePlayerStatOverride

LEAGUEPEDIA_ROLES = {
    "top": "TOP",
    "jungle": "JUNGLE",
    "jng": "JUNGLE",
    "mid": "MID",
    "bot": "ADC",
    "adc": "ADC",
    "support": "SUPPORT",
    "sup": "SUPPORT",
}


def normalize_role(value: str | None) -> str:
    return LEAGUEPEDIA_ROLES.get((value or "").strip().lower(), "")


@dataclass
class Observation:
    game_id: int
    match_id: int
    game_number: int
    leaguepedia_game_id: str | None
    player_id: int
    nickname: str
    team_name: str
    role: str
    champion: str
    kills: int
    deaths: int
    assists: int
    cs: int
    vision_score: int
    win: bool
    played_at: datetime | None
    participated: bool
    overridden: bool
    complete: bool
    score: float | None


def role_map(edition_id: int | None, player_ids: Iterable[int]) -> dict[int, str]:
    ids = set(player_ids)
    if not ids or edition_id is None:
        return {}
    roles: dict[int, str] = {}
    for entry in (
        EditionRoster.objects.filter(edition_id=edition_id, player_id__in=ids)
        .order_by("active_from")
        .values("player_id", "role", "active_to")
    ):
        # L'appartenenza attiva (active_to nullo) prevale su quelle chiuse.
        if entry["player_id"] not in roles or entry["active_to"] is None:
            roles[entry["player_id"]] = entry["role"]
    return roles


def _value(override_value, raw_value) -> int:
    if override_value is not None:
        return override_value
    return raw_value if raw_value is not None else 0


def observations(
    games: QuerySet[EsportsGame] | None = None,
    *,
    edition_id: int | None = None,
    match_ids: Iterable[int] | None = None,
    player_ids: Iterable[int] | None = None,
    include_non_participants: bool = False,
) -> list[Observation]:
    """Osservazioni effettive ordinate per istante di gioco."""
    if games is None:
        games = EsportsGame.objects.all()
    if edition_id is not None:
        games = games.filter(match__edition_id=edition_id)
    if match_ids is not None:
        games = games.filter(match_id__in=list(match_ids))
    games = games.select_related("match")
    game_list = list(games)
    if not game_list:
        return []
    game_by_id = {g.id: g for g in game_list}
    stats = GamePlayerStat.objects.filter(game_id__in=game_by_id, player__isnull=False).select_related(
        "player"
    )
    overrides = GamePlayerStatOverride.objects.filter(game_id__in=game_by_id).select_related("player")
    if player_ids is not None:
        ids = list(player_ids)
        stats = stats.filter(player_id__in=ids)
        overrides = overrides.filter(player_id__in=ids)
    override_by_key = {(o.game_id, o.player_id): o for o in overrides}
    edition_of_game = {g.id: g.match.edition_id for g in game_list}
    stat_list = list(stats)
    all_players = {s.player_id for s in stat_list} | {o.player_id for o in override_by_key.values()}
    roles_by_edition: dict[int | None, dict[int, str]] = {}
    for edition in set(edition_of_game.values()):
        roles_by_edition[edition] = role_map(edition, all_players)

    result: list[Observation] = []
    seen: set[tuple[int, int]] = set()
    for stat in stat_list:
        key = (stat.game_id, stat.player_id)
        if key in seen:
            continue
        seen.add(key)
        game = game_by_id[stat.game_id]
        override = override_by_key.get(key)
        role = roles_by_edition[edition_of_game[game.id]].get(stat.player_id) or stat.role
        result.append(_build(game, stat.player, role, stat, override))
    for key, override in override_by_key.items():
        if key in seen:
            continue
        game = game_by_id[override.game_id]
        role = roles_by_edition[edition_of_game[game.id]].get(override.player_id, "")
        result.append(_build(game, override.player, role, None, override))

    if not include_non_participants:
        result = [o for o in result if o.participated]
    result.sort(key=lambda o: (o.played_at is None, o.played_at or datetime.min, o.game_id, o.player_id))
    return result


def _build(
    game: EsportsGame, player, role: str, stat: GamePlayerStat | None, override: GamePlayerStatOverride | None
) -> Observation:
    raw = stat
    participated = True
    if override is not None and override.participated is not None:
        participated = override.participated
    kills = _value(override.kills if override else None, raw.kills if raw else None)
    deaths = _value(override.deaths if override else None, raw.deaths if raw else None)
    assists = _value(override.assists if override else None, raw.assists if raw else None)
    cs = _value(override.cs if override else None, raw.cs if raw else None)
    vision = _value(override.vision_score if override else None, raw.vision_score if raw else None)
    if override is not None and override.win is not None:
        win = override.win
    else:
        win = bool(raw.win) if raw is not None and raw.win is not None else False
    complete = override is not None or (raw is not None and raw.is_complete)
    score = game_score(role, kills, deaths, assists, cs, vision, win) if role else None
    champion = (override.champion if override and override.champion else "") or (raw.champion if raw else "")
    return Observation(
        game_id=game.id,
        match_id=game.match_id,
        game_number=game.game_number,
        leaguepedia_game_id=game.leaguepedia_game_id,
        player_id=player.id,
        nickname=player.nickname,
        team_name=(raw.source_team_name if raw else "") or "",
        role=role,
        champion=champion,
        kills=kills,
        deaths=deaths,
        assists=assists,
        cs=cs,
        vision_score=vision,
        win=win,
        played_at=game.played_at or game.match.begin_at,
        participated=participated,
        overridden=override is not None,
        complete=complete,
        score=score,
    )
