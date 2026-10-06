"""``LeaguepediaEnrichWorker``: statistiche per game delle serie concluse (ogni 30 minuti).

Prende al massimo ``LEAGUEPEDIA_ENRICH_BATCH_SIZE`` serie ``finished`` senza statistiche, nell'ordine
dell'indice parziale (mai controllate prima, poi le più recenti). Gestisce dati mancanti o parziali
(righe ``MISSING``, game non ancora pubblicati) con ritentativi e give-up dopo N giorni.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils.dateparse import parse_datetime

from apps.common.utils import now
from apps.competitions.models import Competition
from apps.esports.models import (
    EditionRoster,
    EsportsGame,
    EsportsMatch,
    GamePlayerStat,
    MatchStatus,
    PlayerAlias,
    ProPlayer,
    ProTeam,
    Provider,
    StatSource,
    TeamAlias,
)
from apps.esports.observations import normalize_role
from apps.providers.sync_state import record_failure, record_success

from .client import LeaguepediaClient, LeaguepediaRateLimited

logger = logging.getLogger(__name__)

SEARCH_BEFORE = timedelta(hours=6)
SEARCH_AFTER = timedelta(hours=12)
MISSING_LINK = "MISSING"


def _int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _norm(name: str | None) -> str:
    return (name or "").strip().lower()


def leaguepedia_team_name(team: ProTeam) -> str:
    alias = TeamAlias.objects.filter(pandascore_name__iexact=team.name).first()
    if alias is None and team.id:
        alias = TeamAlias.objects.filter(team=team).first()
    if alias is not None:
        return alias.leaguepedia_name
    return team.leaguepedia_name or team.name


class LeaguepediaEnrichWorker:
    def __init__(
        self,
        client: LeaguepediaClient | None = None,
        batch_size: int | None = None,
        give_up_days: int | None = None,
    ):
        self._client = client
        self.batch_size = batch_size or settings.LEAGUEPEDIA_ENRICH_BATCH_SIZE
        self.give_up = timedelta(
            days=give_up_days if give_up_days is not None else settings.LEAGUEPEDIA_GIVE_UP_DAYS
        )

    @property
    def client(self) -> LeaguepediaClient:
        if self._client is None:
            self._client = LeaguepediaClient()
        return self._client

    @staticmethod
    def queue(competition: Competition | None = None):
        qs = EsportsMatch.objects.filter(
            status=MatchStatus.FINISHED, leaguepedia_synced_at__isnull=True, edition__isnull=False
        )
        if competition is not None:
            qs = qs.filter(edition__competition=competition)
        return qs.order_by(
            F("leaguepedia_checked_at").asc(nulls_first=True), F("end_at").desc(nulls_last=True)
        )

    def run(self, competition: Competition | None = None, limit: int | None = None) -> dict:
        if self._client is None and not (
            settings.LEAGUEPEDIA_BOT_USERNAME and settings.LEAGUEPEDIA_BOT_PASSWORD
        ):
            logger.warning("Bot password Leaguepedia assente: arricchimento disattivato, si serve la cache")
            return {"skipped": True}
        report = {
            "skipped": False,
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped_games": 0,
            "failed": 0,
            "unmatched": [],
            "rate_limited": False,
            "errors": [],
            "matches": [],
        }
        touched: dict[int, Competition] = {}
        for match in list(
            self.queue(competition).select_related("edition__competition")[: limit or self.batch_size]
        ):
            touched[match.edition.competition_id] = match.edition.competition
            try:
                self.enrich_match(match, report)
                report["processed"] += 1
            except LeaguepediaRateLimited as error:
                # Il rate limit interrompe l'intero ciclo: si riprova al prossimo giro.
                report["rate_limited"] = True
                report["errors"].append(str(error))
                for comp in touched.values():
                    record_failure(Provider.LEAGUEPEDIA, comp, f"ratelimited: {error}")
                return report
            except Exception as error:
                logger.warning("Arricchimento serie %s fallito: %s", match.id, error)
                report["failed"] += 1
                report["errors"].append(f"match {match.id}: {error}")
                EsportsMatch.objects.filter(pk=match.pk).update(leaguepedia_checked_at=now())
        for comp in touched.values():
            record_success(
                Provider.LEAGUEPEDIA,
                comp,
                error="; ".join(report["errors"][:5]),
                counts={
                    "inserted": report["inserted"],
                    "updated": report["updated"],
                    "skipped": report["skipped_games"],
                    "failed": report["failed"],
                },
                unmatched=report["unmatched"],
            )
        if report["matches"]:
            from apps.matchdays.services import recompute_for_matches

            recompute_for_matches(report["matches"])
        return report

    # ----------------------------------------------------------------- singola serie
    def enrich_match(self, match: EsportsMatch, report: dict) -> None:
        entries = list(match.match_teams.select_related("team").order_by("position"))
        moment = now()
        if len(entries) != 2:
            EsportsMatch.objects.filter(pk=match.pk).update(
                leaguepedia_synced_at=moment, leaguepedia_checked_at=moment
            )
            return
        teams = [e.team for e in entries]
        names = [leaguepedia_team_name(t) for t in teams]
        begin = match.begin_at or match.end_at or moment
        end = match.end_at or begin
        games = self.client.list_games(names[0], names[1], begin - SEARCH_BEFORE, end + SEARCH_AFTER)
        expected = sum(e.score for e in entries) or None
        if not games:
            self._mark_unavailable(match, moment)
            return
        stats = self.client.list_player_stats([g["game_id"] for g in games])
        complete = self._store(match, teams, names, games, stats, report)
        enough = expected is None or len(games) >= expected
        if (complete and enough) or self._expired(match, moment):
            EsportsMatch.objects.filter(pk=match.pk).update(
                leaguepedia_synced_at=moment,
                leaguepedia_checked_at=moment,
                stats_complete=complete and enough,
            )
        else:
            EsportsMatch.objects.filter(pk=match.pk).update(
                leaguepedia_checked_at=moment, stats_complete=False
            )
        report["matches"].append(match.id)

    def _expired(self, match: EsportsMatch, moment) -> bool:
        reference = match.end_at or match.begin_at
        return reference is not None and moment - reference > self.give_up

    def _mark_unavailable(self, match: EsportsMatch, moment) -> None:
        if self._expired(match, moment):
            # Give-up: la serie esce dalla coda; la giornata resta provvisoria fino all'inserimento manuale.
            logger.warning("Serie %s senza statistiche Leaguepedia dopo %s: give-up", match.id, self.give_up)
            EsportsMatch.objects.filter(pk=match.pk).update(
                leaguepedia_synced_at=moment, leaguepedia_checked_at=moment, stats_complete=False
            )
        else:
            EsportsMatch.objects.filter(pk=match.pk).update(leaguepedia_checked_at=moment)

    @transaction.atomic
    def _store(self, match, teams, names, games, stats, report) -> bool:
        team_by_name = {_norm(name): team for name, team in zip(names, teams, strict=False)}
        team_by_name.update({_norm(team.name): team for team in teams})
        stats_by_game: dict[str, list[dict]] = {}
        for row in stats:
            stats_by_game.setdefault(row["game_id"], []).append(row)
        complete = True
        for index, raw in enumerate(games, start=1):
            number = _int(raw.get("game_in_match")) or index
            played_at = (
                parse_datetime((raw.get("datetime_utc") or "").replace(" ", "T") + "+00:00")
                if raw.get("datetime_utc")
                else None
            )
            length = raw.get("length_minutes")
            game = (
                EsportsGame.objects.filter(leaguepedia_game_id=raw["game_id"]).first()
                or EsportsGame.objects.filter(match=match, game_number=number).first()
            )
            created = game is None
            game = game or EsportsGame(match=match, game_number=number)
            game.match = match
            game.game_number = number
            game.leaguepedia_game_id = raw["game_id"]
            game.winner_team = team_by_name.get(_norm(raw.get("win_team")))
            game.length_seconds = int(float(length) * 60) if length not in (None, "") else None
            game.played_at = played_at
            game.mvp_link = raw.get("mvp") or ""
            game.overview_page = raw.get("overview_page") or ""
            game.save()
            report["inserted" if created else "updated"] += 1
            rows = stats_by_game.get(raw["game_id"], [])
            if len(rows) < 10:
                complete = False
            for row in rows:
                complete = self._store_row(game, match, team_by_name, row, report) and complete
        return complete

    def _store_row(self, game, match, team_by_name, row, report) -> bool:
        link = (row.get("link") or "").strip()
        missing = not link or link.upper() == MISSING_LINK
        team = team_by_name.get(_norm(row.get("team")))
        values = {
            k: _int(row.get(k))
            for k in ("kills", "deaths", "assists", "gold", "cs", "damage_to_champions", "vision_score")
        }
        is_complete = not missing and all(
            values[k] is not None for k in ("kills", "deaths", "assists", "cs", "vision_score")
        )
        player = None if missing else self.resolve_player(link, team, match)
        if player is None and not missing:
            report["unmatched"].append(link)
        key = link if not missing else f"{MISSING_LINK}:{row.get('team')}:{row.get('role')}"
        win = row.get("player_win")
        GamePlayerStat.objects.update_or_create(
            game=game,
            leaguepedia_link=key,
            defaults={
                "player": player,
                "team": team,
                "source_team_name": row.get("team") or "",
                "side": {"1": "Blue", "2": "Red"}.get(str(row.get("side")), str(row.get("side") or "")),
                "role": normalize_role(row.get("role")),
                "champion": row.get("champion") or "",
                **values,
                "win": None if win in (None, "") else str(win).lower() in ("yes", "1", "true"),
                "is_complete": is_complete,
                "source": StatSource.LEAGUEPEDIA,
            },
        )
        return is_complete and player is not None

    @staticmethod
    def resolve_player(link: str, team: ProTeam | None, match: EsportsMatch) -> ProPlayer | None:
        player = ProPlayer.objects.filter(leaguepedia_link=link).first()
        if player is not None:
            return player
        alias = PlayerAlias.objects.select_related("player").filter(leaguepedia_link=link).first()
        if alias is not None:
            return alias.player
        nickname = link.split("(")[0].strip()
        roster = EditionRoster.objects.select_related("player").filter(
            edition_id=match.edition_id, player__nickname__iexact=nickname
        )
        if team is not None:
            roster = roster.filter(team=team)
        candidates = {entry.player for entry in roster}
        if len(candidates) == 1:
            player = candidates.pop()
            if not player.leaguepedia_link:
                player.leaguepedia_link = link
                player.save(update_fields=["leaguepedia_link"])
            return player
        return None
