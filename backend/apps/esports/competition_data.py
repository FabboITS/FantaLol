"""Proiezioni pubbliche per competizione (generalizzazione di ``LecDataParser``/``LecLiveDataService``).

Le view leggono solo dal database: un'interruzione dei provider produce dati vecchi con stato ``stale``.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.common.exceptions import ResourceNotFoundException
from apps.common.utils import now
from apps.competitions.models import Competition, CompetitionEdition

from .models import EsportsMatch, MatchStatus, Provider, ProviderSyncState
from .observations import Observation, observations


def get_competition(code: str) -> Competition:
    competition = Competition.objects.filter(code__iexact=code).first()
    if competition is None:
        raise ResourceNotFoundException(f"Competizione non trovata: {code}")
    return competition


def resolve_edition(competition: Competition, edition_id: int | None = None) -> CompetitionEdition | None:
    if edition_id is not None:
        edition = competition.editions.filter(pk=edition_id).first()
        if edition is None:
            raise ResourceNotFoundException(f"Edizione non trovata con id: {edition_id}")
        return edition
    return competition.current_edition()


# --------------------------------------------------------------------------- freschezza
def freshness(competition: Competition | None) -> dict:
    states = (
        list(ProviderSyncState.objects.filter(competition=competition))
        if competition
        else list(ProviderSyncState.objects.all())
    )
    by_provider = {s.provider: s for s in states}
    successes = [s.last_success_at for s in states if s.last_success_at]
    last = max(successes) if successes else None
    failed = any(s.status == "FAILED" for s in states)
    complete = all(
        by_provider.get(p) and by_provider[p].last_success_at
        for p in (Provider.PANDASCORE, Provider.LEAGUEPEDIA)
    )
    status = "stale" if failed else "fresh" if complete else "awaiting-data"
    return {"status": status, "last_updated_at": last}


def cumulative_freshness(competition: Competition) -> dict:
    """Equivalente di ``CumulativeDataFreshnessService`` basato sullo stato Leaguepedia."""
    state = ProviderSyncState.objects.filter(provider=Provider.LEAGUEPEDIA, competition=competition).first()
    if state is None or state.last_success_at is None:
        return {"status": "awaiting-data", "last_updated_at": None, "provisional": True}
    if state.status == "FAILED":
        return {"status": "stale", "last_updated_at": state.last_success_at, "provisional": True}
    return {"status": "fresh", "last_updated_at": state.last_success_at, "provisional": False}


def section(competition: Competition, items: list, provisional: bool) -> dict:
    fresh = freshness(competition)
    return {
        "status": fresh["status"],
        "last_updated_at": fresh["last_updated_at"],
        "provisional": provisional or fresh["status"] != "fresh",
        "items": items,
    }


# --------------------------------------------------------------------------- classifica
def standings(edition: CompetitionEdition | None) -> list[dict]:
    if edition is None:
        return []
    records: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for match in EsportsMatch.objects.filter(edition=edition, status=MatchStatus.FINISHED).prefetch_related(
        "match_teams__team"
    ):
        for entry in match.match_teams.all():
            record = records[entry.team.name]
            if match.winner_team_id and entry.team_id == match.winner_team_id:
                record[0] += 1
            else:
                record[1] += 1
    ordered = sorted(records.items(), key=lambda kv: (-kv[1][0], kv[1][1], kv[0].lower()))
    return [
        {"position": i + 1, "team_name": name, "series_wins": w, "series_losses": loss}
        for i, (name, (w, loss)) in enumerate(ordered)
    ]


# --------------------------------------------------------------------------- prestazioni e partite
def champion_path(name: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9]", "", name or "")
    return (
        f"/Player_immage/Champions/{identifier}.png" if identifier else "/Player_immage/Champions/unknown.svg"
    )


def _team_names(edition: CompetitionEdition, obs_list: list[Observation]) -> dict[int, str]:
    from apps.leagues.services import edition_roster_map

    roster = edition_roster_map(edition.id, {o.player_id for o in obs_list})
    return {pid: entry.team.name for pid, entry in roster.items()}


def performances(edition: CompetitionEdition | None) -> list[dict]:
    if edition is None:
        return []
    obs_list = [o for o in observations(edition_id=edition.id) if o.score is not None]
    teams = _team_names(edition, obs_list)
    grouped: dict[int, list[Observation]] = defaultdict(list)
    for obs in obs_list:
        grouped[obs.player_id].append(obs)
    result = []
    for rows in grouped.values():
        first = rows[0]
        picks = Counter(o.champion for o in rows if o.champion)
        result.append(
            {
                "player_id": first.player_id,
                "nickname": first.nickname,
                "team_name": teams.get(first.player_id) or first.team_name,
                "role": first.role,
                "games_played": len(rows),
                "fantasy_average": sum(o.score for o in rows) / len(rows),
                "champions": [
                    {"champion_name": c, "image_path": champion_path(c), "pick_count": n}
                    for c, n in sorted(picks.items(), key=lambda kv: kv[0].lower())
                ],
            }
        )
    result.sort(key=lambda p: -p["fantasy_average"])
    return result


def _game_player(obs: Observation, team_name: str) -> dict:
    perfect = obs.deaths == 0
    return {
        "player_id": obs.player_id,
        "nickname": obs.nickname,
        "team_name": team_name,
        "role": obs.role,
        "champion_name": obs.champion,
        "champion_image_path": champion_path(obs.champion),
        "kills": obs.kills,
        "deaths": obs.deaths,
        "assists": obs.assists,
        "cs": obs.cs,
        "vision_score": obs.vision_score,
        "kda": None if perfect else (obs.kills + obs.assists) / obs.deaths,
        "perfect_kda": perfect,
        "fantasy_score": obs.score,
        "overridden": obs.overridden,
        "complete": obs.complete,
    }


def matches(edition: CompetitionEdition | None) -> list[dict]:
    if edition is None:
        return []
    obs_list = observations(edition_id=edition.id)
    teams = _team_names(edition, obs_list)
    by_match: dict[int, dict[int, list[Observation]]] = defaultdict(lambda: defaultdict(list))
    for obs in obs_list:
        by_match[obs.match_id][obs.game_id].append(obs)
    zone = ZoneInfo(edition.competition.timezone)
    result = []
    for match in EsportsMatch.objects.filter(pk__in=list(by_match)).prefetch_related("games"):
        games = []
        for game in match.games.all():
            rows = by_match[match.id].get(game.id, [])
            if not rows:
                continue
            games.append(
                {
                    "id": str(game.leaguepedia_game_id or game.id),
                    "label": f"Game {game.game_number}",
                    "players": [_game_player(o, teams.get(o.player_id) or o.team_name) for o in rows],
                }
            )
        result.append(
            {
                "id": str(match.id),
                "name": match.name,
                "date": match.begin_at.astimezone(zone).date() if match.begin_at else None,
                "status": "complete" if match.stats_complete else "partial",
                "games": games,
            }
        )
    result.sort(key=lambda m: (m["date"] is None, -m["date"].toordinal() if m["date"] else 0))
    return result


def game(edition: CompetitionEdition | None, match_id: str, game_id: str) -> dict:
    for match in matches(edition):
        if match["id"] == str(match_id):
            for item in match["games"]:
                if item["id"] == str(game_id):
                    return item
    raise ResourceNotFoundException(f"Game non trovato: {game_id}")


# --------------------------------------------------------------------------- feed partite (pipeline 5.3)
FEED_STATES = {"upcoming", "results", "live"}


def is_stale(competition: Competition | None) -> tuple[bool, object]:
    qs = ProviderSyncState.objects.filter(provider=Provider.PANDASCORE)
    if competition is not None:
        qs = qs.filter(competition=competition)
    last = max((s.last_success_at for s in qs if s.last_success_at), default=None)
    stale = last is None or now() - last > timedelta(minutes=settings.ESPORTS_STALE_AFTER_MINUTES)
    return stale, last


def match_item(match: EsportsMatch) -> dict:
    return {
        "id": match.id,
        "pandascore_id": match.pandascore_id,
        "name": match.name,
        "competition": match.edition.competition.code if match.edition_id else None,
        "edition_id": match.edition_id,
        "stage": match.stage.code if match.stage_id else None,
        "status": match.status,
        "begin_at": match.begin_at,
        "end_at": match.end_at,
        "number_of_games": match.number_of_games,
        "winner_team_id": match.winner_team_id,
        "has_stats": match.games.exists(),
        "stats_complete": match.stats_complete,
        "teams": [
            {
                "id": mt.team_id,
                "name": mt.team.name,
                "acronym": mt.team.acronym,
                "logo_url": mt.team.logo_url,
                "score": mt.score,
                "winner": mt.winner,
            }
            for mt in match.match_teams.all()
        ],
    }


def feed(competition_code: str, state: str, limit: int) -> dict:
    competition = None if competition_code == "all" else get_competition(competition_code)
    qs = EsportsMatch.objects.select_related("edition__competition", "stage").prefetch_related(
        "match_teams__team", "games"
    )
    if competition is not None:
        qs = qs.filter(edition__competition=competition)
    else:
        qs = qs.filter(edition__isnull=False)
    if state == "upcoming":
        qs = qs.filter(status=MatchStatus.NOT_STARTED).order_by("begin_at")
    elif state == "live":
        qs = qs.filter(status=MatchStatus.RUNNING).order_by("begin_at")
    else:
        qs = qs.filter(status=MatchStatus.FINISHED).order_by("-begin_at")
    stale, last = is_stale(competition)
    return {
        "source": "PandaScore",
        "refresh_interval_minutes": 60,
        "last_synced_at": last,
        "verification_required": True,
        "stale": stale,
        "items": [match_item(m) for m in qs[:limit]],
    }


def match_games(match_id: int) -> dict:
    match = EsportsMatch.objects.select_related("edition__competition").filter(pk=match_id).first()
    if match is None:
        raise ResourceNotFoundException(f"Partita non trovata con id: {match_id}")
    obs_list = observations(match_ids=[match.id], include_non_participants=False)
    teams = _team_names(match.edition, obs_list) if match.edition_id else {}
    by_game: dict[int, list[Observation]] = defaultdict(list)
    for obs in obs_list:
        by_game[obs.game_id].append(obs)
    pages = sorted({g.overview_page for g in match.games.all() if g.overview_page})
    attribution = settings.LEAGUEPEDIA_ATTRIBUTION
    if pages:
        attribution += " Fonte: " + ", ".join(
            f"https://lol.fandom.com/wiki/{page.replace(' ', '_')}" for page in pages
        )
    return {
        "source": "Leaguepedia",
        "attribution": attribution,
        "license": "CC BY-SA 3.0",
        "match_id": match.id,
        "items": [
            {
                "id": g.id,
                "game_number": g.game_number,
                "leaguepedia_game_id": g.leaguepedia_game_id,
                "winner_team_id": g.winner_team_id,
                "length_seconds": g.length_seconds,
                "played_at": g.played_at,
                "mvp": g.mvp_link or None,
                "players": [
                    _game_player(o, teams.get(o.player_id) or o.team_name) for o in by_game.get(g.id, [])
                ],
            }
            for g in match.games.all().order_by("game_number")
        ],
    }
