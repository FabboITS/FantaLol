"""``EsportsSyncWorker``: calendario, risultati e roster da PandaScore (ogni 60 minuti).

Regole: i fallimenti parziali sono normali (errori raccolti per elemento, si salva ciò che riesce);
lo stato di ogni competizione finisce in ``ProviderSyncState``; senza token il worker non parte.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from apps.common.utils import now
from apps.competitions.models import (
    Competition,
    CompetitionEdition,
    Ruleset,
    Stage,
    default_policy_for,
    ensure_worlds_stages,
)
from apps.esports.models import (
    EditionRoster,
    EsportsMatch,
    EsportsMatchTeam,
    MatchStatus,
    ProPlayer,
    ProTeam,
    Provider,
)
from apps.providers.sync_state import record_failure, record_success
from apps.worlds.stages import detect_stage_code

from .client import MATCH_STATES, PandaScoreClient, PandaScoreNotConfigured

logger = logging.getLogger(__name__)

MAX_PAGES = 10
ROLE_MAP = {
    "top": "TOP",
    "jun": "JUNGLE",
    "jungle": "JUNGLE",
    "mid": "MID",
    "adc": "ADC",
    "bot": "ADC",
    "sup": "SUPPORT",
    "support": "SUPPORT",
}
STATUS_MAP = {s.value: s.value for s in MatchStatus}
WORLDS_SEARCH_NAME = "World Championship"


def _dt(value) -> datetime | None:
    return parse_datetime(value) if value else None


class EsportsSyncWorker:
    def __init__(self, client: PandaScoreClient | None = None):
        self._client = client

    @property
    def client(self) -> PandaScoreClient:
        if self._client is None:
            self._client = PandaScoreClient()
        return self._client

    # ----------------------------------------------------------------- entry point
    def run(self, competition_code: str | None = None, *, discover: bool = False) -> dict:
        if self._client is None and not settings.PANDASCORE_API_TOKEN:
            logger.warning("PANDASCORE_API_TOKEN assente: sync PandaScore disattivato, si serve la cache")
            return {"skipped": True, "competitions": {}}
        report: dict = {"skipped": False, "competitions": {}}
        competitions = Competition.objects.all()
        if competition_code:
            competitions = competitions.filter(code__iexact=competition_code)
        for competition in competitions:
            try:
                if competition.pandascore_league_id is None:
                    self.resolve_league_id(competition)
                if competition.pandascore_league_id is None:
                    continue
                if discover:
                    self.discover_editions(competition)
                if not competition.editions.filter(is_active=True).exists():
                    continue
                result = self.sync_competition(competition)
                report["competitions"][competition.code] = result
                record_success(
                    Provider.PANDASCORE,
                    competition,
                    error="; ".join(result["errors"][:5]) if result["errors"] else "",
                )
            except PandaScoreNotConfigured:
                raise
            except Exception as error:  # una lega che fallisce non blocca le altre
                logger.exception("Sync PandaScore fallito per %s", competition.code)
                record_failure(Provider.PANDASCORE, competition, error)
                report["competitions"][competition.code] = {"error": str(error)}
        return report

    # ----------------------------------------------------------------- leghe ed edizioni
    def resolve_league_id(self, competition: Competition) -> int | None:
        if competition.code != "WORLDS":
            return competition.pandascore_league_id
        candidates = self.client.search_leagues(WORLDS_SEARCH_NAME)
        exact = [c for c in candidates if (c.get("name") or "").strip().lower() == WORLDS_SEARCH_NAME.lower()]
        chosen = (exact or candidates or [None])[0]
        if chosen and chosen.get("id"):
            competition.pandascore_league_id = chosen["id"]
            competition.save(update_fields=["pandascore_league_id"])
            logger.info("ID PandaScore WORLDS risolto: %s", chosen["id"])
        return competition.pandascore_league_id

    def discover_editions(self, competition: Competition) -> list[CompetitionEdition]:
        created = []
        horizon = now() - timedelta(days=60)
        for serie in self.client.league_series(competition.pandascore_league_id):
            begin, end = _dt(serie.get("begin_at")), _dt(serie.get("end_at"))
            if begin is None or (end is not None and end < horizon):
                continue
            tournaments = serie.get("tournaments") or []
            label = serie.get("full_name") or serie.get("name") or serie.get("year")
            name = f"{competition.code} {label}".strip()
            edition, was_created = CompetitionEdition.objects.get_or_create(
                pandascore_serie_id=serie["id"],
                defaults={
                    "competition": competition,
                    "year": serie.get("year") or begin.year,
                    "name": name,
                    "starts_at": begin,
                    "ends_at": end,
                    "pandascore_tournament_ids": [t["id"] for t in tournaments if t.get("id")],
                    "is_active": begin - timedelta(days=30) <= now() <= (end or now()) + timedelta(days=7),
                    "lineup_policy": default_policy_for(competition),
                },
            )
            if not was_created:
                ids = sorted(
                    set(edition.pandascore_tournament_ids) | {t["id"] for t in tournaments if t.get("id")}
                )
                edition.pandascore_tournament_ids = ids
                edition.ends_at = end or edition.ends_at
                edition.save(update_fields=["pandascore_tournament_ids", "ends_at"])
            if competition.ruleset == Ruleset.WORLDS:
                self._map_worlds_stages(edition, tournaments)
            created.append(edition)
        return created

    def _map_worlds_stages(self, edition: CompetitionEdition, tournaments: list[dict]) -> None:
        stages = {s.code: s for s in ensure_worlds_stages(edition)}
        for tournament in tournaments:
            code = detect_stage_code(tournament.get("name"), None)
            if code and code in stages:
                stage = stages[code]
                stage.pandascore_tournament_id = tournament.get("id")
                stage.starts_at = _dt(tournament.get("begin_at")) or stage.starts_at
                stage.ends_at = _dt(tournament.get("end_at")) or stage.ends_at
                stage.save()

    # ----------------------------------------------------------------- calendario e risultati
    def sync_competition(self, competition: Competition) -> dict:
        editions = list(competition.editions.filter(is_active=True))
        errors: list[str] = []
        upserted = 0
        tournaments: dict[int, set[int]] = {e.id: set(e.pandascore_tournament_ids) for e in editions}
        earliest = min(e.starts_at for e in editions) - timedelta(days=1)
        ends = [e.ends_at for e in editions]
        latest = None if any(end is None for end in ends) else max(ends) + timedelta(days=1)
        for state in MATCH_STATES:
            page = 1
            while page <= MAX_PAGES:
                result = self.client.league_matches(competition.pandascore_league_id, state, page=page)
                outside = False
                for raw in result.items:
                    begin = _dt(raw.get("begin_at") or raw.get("scheduled_at"))
                    if state == "past" and begin and begin < earliest:
                        outside = True
                        continue
                    if state == "upcoming" and begin and latest and begin > latest:
                        outside = True
                        continue
                    try:
                        edition = self.map_edition(raw, editions)
                        if edition is None:
                            continue
                        self.upsert_match(raw, edition)
                        if raw.get("tournament_id"):
                            tournaments[edition.id].add(raw["tournament_id"])
                        upserted += 1
                    except Exception as error:
                        logger.warning("Match PandaScore %s non salvato: %s", raw.get("id"), error)
                        errors.append(f"match {raw.get('id')}: {error}")
                if outside or not result.has_next:
                    break
                page += 1
        rosters = 0
        for edition in editions:
            known = sorted(tournaments[edition.id])
            if known != sorted(edition.pandascore_tournament_ids):
                edition.pandascore_tournament_ids = known
                edition.save(update_fields=["pandascore_tournament_ids"])
            for tournament_id in known:
                try:
                    rosters += self.sync_rosters(edition, tournament_id)
                except Exception as error:
                    logger.warning("Roster torneo %s non sincronizzato: %s", tournament_id, error)
                    errors.append(f"roster {tournament_id}: {error}")
        return {"matches": upserted, "roster_players": rosters, "errors": errors}

    @staticmethod
    def map_edition(raw: dict, editions: list[CompetitionEdition]) -> CompetitionEdition | None:
        serie_id, tournament_id = raw.get("serie_id"), raw.get("tournament_id")
        for edition in editions:
            if serie_id and serie_id == edition.pandascore_serie_id:
                return edition
            if tournament_id and tournament_id in edition.pandascore_tournament_ids:
                return edition
        begin = _dt(raw.get("begin_at") or raw.get("scheduled_at"))
        for edition in editions:
            if (
                edition.pandascore_serie_id is None
                and not edition.pandascore_tournament_ids
                and begin
                and edition.starts_at <= begin
                and (edition.ends_at is None or begin <= edition.ends_at)
            ):
                return edition
        return None

    @transaction.atomic
    def upsert_team(self, data: dict) -> ProTeam:
        team, _ = ProTeam.objects.update_or_create(
            pandascore_id=data["id"],
            defaults={
                "name": data.get("name") or "",
                "acronym": data.get("acronym") or "",
                "slug": data.get("slug") or slugify(data.get("name") or ""),
                "location": data.get("location") or "",
                "image_url_light": data.get("image_url") or "",
                "image_url_dark": data.get("dark_mode_image_url") or "",
            },
        )
        return team

    @transaction.atomic
    def upsert_match(self, raw: dict, edition: CompetitionEdition) -> EsportsMatch:
        opponents = [o.get("opponent") for o in raw.get("opponents") or [] if o.get("opponent")]
        teams = [self.upsert_team(o) for o in opponents]
        by_pandascore = {t.pandascore_id: t for t in teams}
        winner = by_pandascore.get(raw.get("winner_id"))
        tournament_name = (raw.get("tournament") or {}).get("name") or ""
        stage = self._stage_for(edition, tournament_name, raw)
        match, _ = EsportsMatch.objects.update_or_create(
            pandascore_id=raw["id"],
            defaults={
                "edition": edition,
                "stage": stage,
                "name": raw.get("name") or " vs ".join(t.name for t in teams),
                "status": STATUS_MAP.get(raw.get("status"), MatchStatus.NOT_STARTED),
                "begin_at": _dt(raw.get("begin_at") or raw.get("scheduled_at")),
                "end_at": _dt(raw.get("end_at")),
                "number_of_games": raw.get("number_of_games") or 1,
                "winner_team": winner,
                "pandascore_tournament_id": raw.get("tournament_id"),
                "pandascore_serie_id": raw.get("serie_id"),
                "tournament_name": tournament_name,
            },
        )
        scores = {r.get("team_id"): r.get("score") or 0 for r in raw.get("results") or []}
        for position, team in enumerate(teams, start=1):
            EsportsMatchTeam.objects.update_or_create(
                match=match,
                team=team,
                defaults={
                    "position": position,
                    "score": scores.get(team.pandascore_id, 0),
                    "winner": winner is not None and winner.id == team.id,
                },
            )
        return match

    def _stage_for(self, edition: CompetitionEdition, tournament_name: str, raw: dict) -> Stage | None:
        if edition.competition.ruleset != Ruleset.WORLDS:
            return None
        stages = {s.code: s for s in ensure_worlds_stages(edition)}
        code = detect_stage_code(tournament_name, raw.get("name"))
        if code is None:
            for stage in stages.values():
                if stage.pandascore_tournament_id and stage.pandascore_tournament_id == raw.get(
                    "tournament_id"
                ):
                    code = stage.code
                    break
        if code is None:
            logger.warning(
                "Torneo Worlds non riconosciuto: '%s' (match %s): stage nullo", tournament_name, raw.get("id")
            )
            return None
        return stages.get(code)

    # ----------------------------------------------------------------- roster
    @transaction.atomic
    def sync_rosters(self, edition: CompetitionEdition, tournament_id: int) -> int:
        count = 0
        default_price = (
            10 if edition.competition.ruleset == Ruleset.WORLDS else settings.REGIONAL_DEFAULT_QUOTAZIONE
        )
        for roster in self.client.tournament_rosters(tournament_id):
            team_data = roster.get("team") if isinstance(roster.get("team"), dict) else roster
            if not team_data.get("id"):
                continue
            team = self.upsert_team(team_data)
            for data in roster.get("players") or []:
                role = ROLE_MAP.get((data.get("role") or "").lower())
                if not role or not data.get("id"):
                    continue
                real_name = " ".join(p for p in (data.get("first_name"), data.get("last_name")) if p)
                player, _ = ProPlayer.objects.update_or_create(
                    pandascore_id=data["id"],
                    defaults={
                        "nickname": data.get("name") or "",
                        "real_name": real_name,
                        "nationality": data.get("nationality") or "",
                        "image_url": data.get("image_url") or "",
                    },
                )
                self._upsert_roster_entry(edition, team, player, role, default_price)
                count += 1
        return count

    @staticmethod
    def _upsert_roster_entry(edition, team, player, role, default_price) -> None:
        current = EditionRoster.objects.filter(edition=edition, player=player, active_to__isnull=True).first()
        if current is not None and current.team_id == team.id:
            if current.role != role and not current.quotazione_set_by_admin:
                current.role = role
                current.save(update_fields=["role"])
            return
        moment = now()
        price, by_admin = default_price, False
        if current is not None:
            # Cambio di squadra durante lo split: si chiude il periodo precedente, la quotazione resta.
            current.active_to = moment
            current.save(update_fields=["active_to"])
            price, by_admin = current.quotazione, current.quotazione_set_by_admin
        EditionRoster.objects.create(
            edition=edition,
            team=team,
            player=player,
            role=role,
            quotazione=price,
            quotazione_set_by_admin=by_admin,
            active_from=edition.starts_at if current is None else moment,
        )
