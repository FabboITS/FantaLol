"""Logica di sincronizzazione: upsert serie, enrich box score, ricalcolo punti.

Due principi conservati dalla pipeline sorgente:
 1. nessuna richiesta del frontend raggiunge mai un provider esterno;
 2. il fallimento parziale è normale: l'errore di una lega/serie non interrompe
    il ciclo, viene solo registrato in `SyncState`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from teams.models import PlayerRole, ProPlayer, ProTeam

from .leaguepedia_client import LeaguepediaClient, LeaguepediaError
from .models import (
    Game,
    GamePlayerStat,
    Match,
    MatchStatus,
    PlayerAlias,
    SyncState,
    SyncStatus,
    TeamAlias,
)
from .pandascore_client import PandaScoreClient, PandaScoreError, supported_leagues

logger = logging.getLogger(__name__)

PANDASCORE_PROVIDER = "PANDASCORE"
LEAGUEPEDIA_PROVIDER = "LEAGUEPEDIA"

#: Finestra allargata usata per agganciare la serie PandaScore ai game Leaguepedia.
ENRICH_WINDOW_BEFORE = timedelta(hours=6)
ENRICH_WINDOW_AFTER = timedelta(hours=12)

ROLE_MAP = {
    "top": PlayerRole.TOP.value,
    "jungle": PlayerRole.JUNGLE.value,
    "jng": PlayerRole.JUNGLE.value,
    "mid": PlayerRole.MID.value,
    "middle": PlayerRole.MID.value,
    "bot": PlayerRole.ADC.value,
    "adc": PlayerRole.ADC.value,
    "support": PlayerRole.SUPPORT.value,
    "sup": PlayerRole.SUPPORT.value,
}


@dataclass
class SyncReport:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "SyncReport") -> None:
        self.inserted += other.inserted
        self.updated += other.updated
        self.skipped += other.skipped
        self.failed += other.failed
        self.errors.extend(other.errors)

    @property
    def status(self) -> str:
        if self.failed and (self.inserted or self.updated):
            return SyncStatus.PARTIAL
        if self.failed:
            return SyncStatus.ERROR
        return SyncStatus.OK


def record_sync_state(provider: str, report: SyncReport, *, success: bool) -> SyncState:
    now = timezone.now()
    state, _ = SyncState.objects.get_or_create(provider=provider)
    state.status = report.status
    state.last_attempt_at = now
    if success and report.status != SyncStatus.ERROR:
        state.last_success_at = now
    state.last_error = "; ".join(report.errors)[:1000] or None
    state.inserted = report.inserted
    state.updated = report.updated
    state.skipped = report.skipped
    state.failed = report.failed
    state.details = {"errors": report.errors[:50]}
    state.save()
    return state


# --------------------------------------------------------------------------
# PandaScore: calendario / stato / risultati
# --------------------------------------------------------------------------
def _parse_dt(raw):
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is not None and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.utc)
    return parsed


def _match_defaults(payload: dict, league_code: str) -> dict:
    opponents = [
        (opponent.get("opponent") or {}).get("name")
        for opponent in payload.get("opponents", []) or []
    ]
    winner = payload.get("winner") or {}
    return {
        "slug": payload.get("slug"),
        "name": payload.get("name"),
        "league_code": league_code,
        "league_pandascore_id": (payload.get("league") or {}).get("id") or payload.get("league_id"),
        "tournament_name": (payload.get("tournament") or {}).get("name"),
        "serie_name": (payload.get("serie") or {}).get("full_name") or (payload.get("serie") or {}).get("name"),
        "status": payload.get("status") or MatchStatus.NOT_STARTED,
        "begin_at": _parse_dt(payload.get("begin_at") or payload.get("scheduled_at")),
        "end_at": _parse_dt(payload.get("end_at")),
        "number_of_games": payload.get("number_of_games") or 0,
        "opponents": [name for name in opponents if name],
        "results": payload.get("results") or [],
        "winner_name": winner.get("name"),
    }


@transaction.atomic
def upsert_match(payload: dict, league_code: str) -> tuple[Match, bool]:
    pandascore_id = payload.get("id")
    if not pandascore_id:
        raise ValueError("Payload PandaScore senza id")
    match, created = Match.objects.update_or_create(
        pandascore_id=pandascore_id,
        defaults=_match_defaults(payload, league_code),
    )
    return match, created


def sync_pandascore(client: PandaScoreClient | None = None) -> SyncReport:
    """Loop lega x stato, upsert idempotente, mai abortito su singolo errore."""
    client = client or PandaScoreClient()
    report = SyncReport()
    if not client.configured:
        report.skipped += 1
        report.errors.append("PANDASCORE_API_TOKEN assente: si serve solo la cache")
        record_sync_state(PANDASCORE_PROVIDER, report, success=False)
        return report

    for league in supported_leagues():
        for state in ("past", "running", "upcoming"):
            try:
                payloads = client.matches_by_league_and_state(league.pandascore_id, state)
            except (PandaScoreError, ValueError) as exc:
                report.failed += 1
                report.errors.append(f"{league.code}/{state}: {exc}")
                logger.warning("Sync PandaScore fallito per %s/%s: %s", league.code, state, exc)
                continue
            for payload in payloads:
                try:
                    _, created = upsert_match(payload, league.code)
                except Exception as exc:  # pragma: no cover - difensivo
                    report.failed += 1
                    report.errors.append(f"{league.code}/{state}/{payload.get('id')}: {exc}")
                    continue
                if created:
                    report.inserted += 1
                else:
                    report.updated += 1

    record_sync_state(PANDASCORE_PROVIDER, report, success=True)
    return report


# --------------------------------------------------------------------------
# Leaguepedia: box score per game
# --------------------------------------------------------------------------
def canonical_team_name(source_name: str) -> str:
    alias = TeamAlias.objects.filter(source_name__iexact=source_name).first()
    return alias.canonical_name if alias else source_name


def resolve_team(name: str) -> ProTeam | None:
    alias = TeamAlias.objects.filter(source_name__iexact=name).select_related("team").first()
    if alias and alias.team_id:
        return alias.team
    canonical = alias.canonical_name if alias else name
    return (ProTeam.objects.filter(leaguepedia_name__iexact=canonical).first()
            or ProTeam.objects.filter(nome__iexact=canonical).first()
            or ProTeam.objects.filter(sigla__iexact=canonical).first())


def resolve_player(link: str, name: str | None = None) -> ProPlayer | None:
    """Mappa il `Link` Leaguepedia sul player interno, via alias se serve."""
    for candidate in filter(None, (link, name)):
        alias = (PlayerAlias.objects.filter(source_name__iexact=candidate)
                 .select_related("player").first())
        if alias and alias.player_id:
            return alias.player
        canonical = alias.canonical_name if alias else candidate
        player = (ProPlayer.objects.filter(leaguepedia_link__iexact=canonical).first()
                  or ProPlayer.objects.filter(nickname__iexact=canonical).first())
        if player:
            return player
    return None


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_bool(value) -> bool:
    return str(value).strip() in {"1", "Yes", "yes", "true", "True"}


def _normalize_role(raw: str | None) -> str | None:
    if not raw:
        return None
    return ROLE_MAP.get(raw.strip().lower())


def enrich_match(match: Match, client: LeaguepediaClient, *, now=None) -> SyncReport:
    """Arricchisce una serie con i box score Leaguepedia e ricalcola i punti."""
    from scoring.services import recompute_scores_for_game

    now = now or timezone.now()
    report = SyncReport()
    match.leaguepedia_checked_at = now
    match.leaguepedia_attempts += 1

    if len(match.opponents) != 2 or match.begin_at is None:
        match.leaguepedia_error = "Serie senza due opponent o senza begin_at"
        report.skipped += 1
        match.save(update_fields=["leaguepedia_checked_at", "leaguepedia_attempts", "leaguepedia_error"])
        return report

    teams = [canonical_team_name(name) for name in match.opponents]
    begin = match.begin_at - ENRICH_WINDOW_BEFORE
    end = (match.end_at or match.begin_at) + ENRICH_WINDOW_AFTER

    try:
        rows = client.games_for_window(teams, begin, end)
    except LeaguepediaError as exc:
        match.leaguepedia_error = str(exc)[:1000]
        report.failed += 1
        report.errors.append(f"match {match.pandascore_id}: {exc}")
        match.save(update_fields=["leaguepedia_checked_at", "leaguepedia_attempts", "leaguepedia_error"])
        return report

    if not rows:
        match.leaguepedia_error = "Nessun game trovato nella finestra temporale"
        report.skipped += 1
        match.save(update_fields=["leaguepedia_checked_at", "leaguepedia_attempts", "leaguepedia_error"])
        return report

    game_ids = [row.get("GameId") for row in rows if row.get("GameId")]
    try:
        player_rows = client.player_stats_for_games(game_ids)
    except LeaguepediaError as exc:
        match.leaguepedia_error = str(exc)[:1000]
        report.failed += 1
        report.errors.append(f"match {match.pandascore_id} box score: {exc}")
        match.save(update_fields=["leaguepedia_checked_at", "leaguepedia_attempts", "leaguepedia_error"])
        return report

    stats_by_game: dict[str, list[dict]] = {}
    for row in player_rows:
        stats_by_game.setdefault(row.get("GameId"), []).append(row)

    unmatched: list[str] = []
    with transaction.atomic():
        for index, row in enumerate(rows, start=1):
            game_id = row.get("GameId")
            if not game_id:
                continue
            played_at = _parse_dt((row.get("DateTime_UTC") or "").replace(" ", "T") + "Z")
            game, created = Game.objects.update_or_create(
                external_game_id=game_id,
                defaults={
                    "match": match,
                    "game_number": _to_int(row.get("N_GameInMatch"), index),
                    "played_at": played_at or match.begin_at,
                    "duration_seconds": int(float(row.get("Gamelength_Number") or 0) * 60) or None,
                    "patch": row.get("Patch"),
                    "winner_name": row.get("Team1") if row.get("WinTeam") == row.get("Team1")
                    else row.get("WinTeam"),
                    "mvp_link": row.get("MVP"),
                    "mvp_player": resolve_player(row.get("MVP") or ""),
                },
            )
            report.inserted += 1 if created else 0
            report.updated += 0 if created else 1

            for stat_row in stats_by_game.get(game_id, []):
                link = stat_row.get("Link") or ""
                player = resolve_player(link, stat_row.get("Name"))
                if player is None:
                    unmatched.append(link or stat_row.get("Name") or "?")
                    continue
                role = _normalize_role(stat_row.get("Role")) or player.ruolo
                stat, _ = GamePlayerStat.objects.update_or_create(
                    game=game,
                    player=player,
                    defaults={
                        "source_link": link,
                        "source_team_name": stat_row.get("Team"),
                        "role": role,
                        "champion": stat_row.get("Champion"),
                        "kills": _to_int(stat_row.get("Kills")),
                        "deaths": _to_int(stat_row.get("Deaths")),
                        "assists": _to_int(stat_row.get("Assists")),
                        "cs": _to_int(stat_row.get("CS")),
                        "gold": _to_int(stat_row.get("Gold")),
                        "damage": _to_int(stat_row.get("DamageToChampions")),
                        "vision_score": _to_int(stat_row.get("VisionScore")),
                        "win": _to_bool(stat_row.get("PlayerWin")),
                    },
                )
                if stat.overridden:
                    continue
            # Il ricalcolo dei fantapunti è agganciato all'enrich: è la
            # differenza sostanziale rispetto alla pipeline read-only sorgente.
            recompute_scores_for_game(game)

        match.leaguepedia_synced_at = now
        match.leaguepedia_error = ("Player non mappati: " + ", ".join(sorted(set(unmatched))))[:1000] \
            if unmatched else None
        match.save(update_fields=["leaguepedia_checked_at", "leaguepedia_attempts",
                                  "leaguepedia_synced_at", "leaguepedia_error"])

    if unmatched:
        report.errors.append(f"match {match.pandascore_id}: player non mappati {sorted(set(unmatched))}")
    return report


def matches_to_enrich(limit: int, *, now=None):
    """Serie finite e non ancora arricchite, le più vecchie prima.

    Le serie più vecchie di `GIVE_UP_AFTER_DAYS` vengono abbandonate, come
    nella pipeline sorgente (nessun retry infinito).
    """
    now = now or timezone.now()
    give_up_before = now - timedelta(days=settings.LEAGUEPEDIA["GIVE_UP_AFTER_DAYS"])
    return (Match.objects
            .filter(status=MatchStatus.FINISHED, leaguepedia_synced_at__isnull=True)
            .filter(end_at__gte=give_up_before)
            .order_by("leaguepedia_checked_at", "end_at")[:limit])


def enrich_leaguepedia(client: LeaguepediaClient | None = None, limit: int | None = None) -> SyncReport:
    client = client or LeaguepediaClient()
    report = SyncReport()
    if not client.configured:
        report.skipped += 1
        report.errors.append(
            "Credenziali Leaguepedia assenti: si servono solo i game già arricchiti")
        record_sync_state(LEAGUEPEDIA_PROVIDER, report, success=False)
        return report

    limit = limit or settings.LEAGUEPEDIA["ENRICH_BATCH_SIZE"]
    for match in list(matches_to_enrich(limit)):
        try:
            report.merge(enrich_match(match, client))
        except Exception as exc:  # pragma: no cover - difensivo
            report.failed += 1
            report.errors.append(f"match {match.pandascore_id}: {exc}")
            logger.exception("Enrich fallito per la serie %s", match.pandascore_id)
    record_sync_state(LEAGUEPEDIA_PROVIDER, report, success=True)
    return report
