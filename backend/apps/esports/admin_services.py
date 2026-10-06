"""Operazioni dell'admin globale sui dati reali: correzioni manuali, alias, game manuali."""

from __future__ import annotations

from django.db import transaction

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException

from .models import (
    EsportsGame,
    EsportsMatch,
    GamePlayerStat,
    GamePlayerStatOverride,
    PlayerAlias,
    ProPlayer,
    ProTeam,
    TeamAlias,
)
from .observations import observations

OVERRIDE_FIELDS = ("participated", "kills", "deaths", "assists", "cs", "vision_score", "win")


def find_game(game_ref: str) -> EsportsGame:
    game = None
    if str(game_ref).isdigit():
        game = EsportsGame.objects.select_related("match").filter(pk=int(game_ref)).first()
    if game is None:
        game = EsportsGame.objects.select_related("match").filter(leaguepedia_game_id=game_ref).first()
    if game is None:
        raise ResourceNotFoundException(f"Game non trovato: {game_ref}")
    return game


def _recompute(game: EsportsGame) -> None:
    from apps.matchdays.services import recompute_for_matches

    recompute_for_matches([game.match_id])


def correction_response(game: EsportsGame, player_id: int) -> dict:
    rows = observations(
        EsportsGame.objects.filter(pk=game.pk), player_ids=[player_id], include_non_participants=True
    )
    row = rows[0] if rows else None
    return {
        "game_id": game.id,
        "leaguepedia_game_id": game.leaguepedia_game_id,
        "player_id": player_id,
        "participated": row.participated if row else None,
        "kills": row.kills if row else None,
        "deaths": row.deaths if row else None,
        "assists": row.assists if row else None,
        "cs": row.cs if row else None,
        "vision_score": row.vision_score if row else None,
        "win": row.win if row else None,
        "fantasy_score": row.score if row else None,
        "overridden": bool(row and row.overridden),
    }


@transaction.atomic
def correct(game_ref: str, player_id: int, values: dict, actor: str) -> dict:
    game = find_game(game_ref)
    player = ProPlayer.objects.filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFoundException(f"Player non trovato con id: {player_id}")
    override, _ = GamePlayerStatOverride.objects.get_or_create(game=game, player=player)
    for name in OVERRIDE_FIELDS:
        setattr(override, name, values.get(name))
    override.champion = values.get("champion") or override.champion
    override.actor = actor
    override.save()
    _recompute(game)
    return correction_response(game, player_id)


@transaction.atomic
def restore(game_ref: str, player_id: int) -> dict:
    game = find_game(game_ref)
    deleted, _ = GamePlayerStatOverride.objects.filter(game=game, player_id=player_id).delete()
    if not deleted and not GamePlayerStat.objects.filter(game=game, player_id=player_id).exists():
        raise ResourceNotFoundException(f"Player-game non trovato: {game_ref}/{player_id}")
    _recompute(game)
    return correction_response(game, player_id)


@transaction.atomic
def create_manual_game(match_id: int, game_number: int, winner_team_id: int | None, played_at) -> EsportsGame:
    match = EsportsMatch.objects.filter(pk=match_id).first()
    if match is None:
        raise ResourceNotFoundException(f"Partita non trovata con id: {match_id}")
    if EsportsGame.objects.filter(match=match, game_number=game_number).exists():
        raise BusinessRuleException(f"Il game {game_number} esiste già per questa serie")
    return EsportsGame.objects.create(
        match=match,
        game_number=game_number,
        winner_team_id=winner_team_id,
        played_at=played_at or match.begin_at,
    )


def unmatched_stats(limit: int = 200) -> list[dict]:
    rows = (
        GamePlayerStat.objects.select_related("game__match__edition__competition", "team")
        .filter(player__isnull=True)
        .exclude(leaguepedia_link__startswith="MISSING")
        .order_by("-game__played_at", "id")[:limit]
    )
    return [
        {
            "id": row.id,
            "game_id": row.game_id,
            "leaguepedia_game_id": row.game.leaguepedia_game_id,
            "match_id": row.game.match_id,
            "match_name": row.game.match.name,
            "competition": row.game.match.edition.competition.code if row.game.match.edition_id else None,
            "leaguepedia_link": row.leaguepedia_link,
            "team_name": row.source_team_name,
            "role": row.role,
            "champion": row.champion,
        }
        for row in rows
    ]


@transaction.atomic
def create_team_alias(pandascore_name: str, leaguepedia_name: str, team_id: int | None) -> TeamAlias:
    team = None
    if team_id is not None:
        team = ProTeam.objects.filter(pk=team_id).first()
        if team is None:
            raise ResourceNotFoundException(f"Team non trovato con id: {team_id}")
    alias, _ = TeamAlias.objects.update_or_create(
        pandascore_name=pandascore_name, defaults={"leaguepedia_name": leaguepedia_name, "team": team}
    )
    return alias


@transaction.atomic
def create_player_alias(leaguepedia_link: str, player_id: int) -> PlayerAlias:
    player = ProPlayer.objects.filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFoundException(f"Player non trovato con id: {player_id}")
    alias, _ = PlayerAlias.objects.update_or_create(
        leaguepedia_link=leaguepedia_link, defaults={"player": player}
    )
    rows = GamePlayerStat.objects.filter(leaguepedia_link=leaguepedia_link, player__isnull=True)
    match_ids = set(rows.values_list("game__match_id", flat=True))
    rows.update(player=player)
    if match_ids:
        from apps.matchdays.services import recompute_for_matches

        recompute_for_matches(match_ids)
    return alias
