"""Importazione dei dati del backend Java (MySQL) nell'edizione "LEC 2026 Summer".

Idempotente: ogni entità è ricondotta a una chiave naturale (username, nome team, nickname, codice invito,
numero di giornata, ...). Gli hash BCrypt sono conservati (``bcrypt$<hash>``, hasher BCrypt abilitato) e i
punteggi storici mantengono la ``formula_version`` originale.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from django.db import transaction
from django.utils.text import slugify

from apps.competitions.models import (
    Competition,
    CompetitionEdition,
    ScoringFormulaVersion,
    default_policy_for,
)
from apps.esports.models import EditionRoster, ProPlayer, ProTeam
from apps.leagues.models import FantaTeam, League, RosterEntry
from apps.lineups.models import EffectiveLineupPeriod
from apps.matchdays.models import Formation, Matchday, MatchdayStatus, PlayerStat

from .models import Role, User, UserProfile

LEGACY_EDITION = "LEC 2026 Summer"
LEGACY_START = datetime(2026, 7, 23, 22, tzinfo=UTC)  # 2026-07-24T00:00+02:00 (backfill-from del Java)
TABLES = [
    "users",
    "user_profiles",
    "lec_teams",
    "lec_players",
    "leagues",
    "fanta_teams",
    "roster_entries",
    "matchdays",
    "player_stats",
    "formations",
    "formation_titolari",
    "effective_lineup_periods",
]


def _dt(value):
    if value is None or isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def legacy_edition() -> CompetitionEdition:
    lec = Competition.objects.get(code="LEC")
    edition, _ = CompetitionEdition.objects.get_or_create(
        competition=lec,
        name=LEGACY_EDITION,
        defaults={
            "year": 2026,
            "starts_at": LEGACY_START,
            "is_active": False,
            "scoring_formula_version": ScoringFormulaVersion.SUMMER_2026_V1,
            "lineup_policy": default_policy_for(lec),
        },
    )
    return edition


@transaction.atomic
def import_rows(rows: dict[str, list[dict]]) -> dict:
    report: Counter = Counter()
    edition = legacy_edition()
    users, teams, players, leagues, fanta, matchdays, formations = {}, {}, {}, {}, {}, {}, {}

    for row in rows.get("users", []):
        password = row["password"]
        if password.startswith("$2"):
            password = f"bcrypt${password}"
        user, created = User.objects.get_or_create(
            username=row["username"],
            defaults={
                "email": row["email"],
                "password": password,
                "role": row.get("role") or Role.USER,
                "is_active": bool(row.get("enabled", True)),
            },
        )
        users[row["id"]] = user
        report["users_created" if created else "users_existing"] += 1
    for row in rows.get("user_profiles", []):
        if row["user_id"] in users:
            UserProfile.objects.update_or_create(
                user=users[row["user_id"]],
                defaults={
                    "nome_visualizzato": row.get("nome_visualizzato"),
                    "bio": row.get("bio"),
                    "avatar_url": row.get("avatar_url"),
                    "summoner_name": row.get("summoner_name"),
                },
            )
            report["profiles"] += 1

    for row in rows.get("lec_teams", []):
        team = ProTeam.objects.filter(name__iexact=row["nome"]).first() or ProTeam.objects.create(
            name=row["nome"],
            acronym=row.get("sigla") or "",
            slug=slugify(row["nome"]),
            image_url_light=row.get("logo_url") or "",
        )
        teams[row["id"]] = team
        report["teams"] += 1
    for row in rows.get("lec_players", []):
        team = teams.get(row["team_id"])
        player = (
            ProPlayer.objects.filter(
                nickname__iexact=row["nickname"], edition_rosters__edition=edition
            ).first()
            or ProPlayer.objects.filter(nickname__iexact=row["nickname"]).first()
            or ProPlayer.objects.create(
                nickname=row["nickname"],
                real_name=row.get("nome_reale") or "",
                nationality=row.get("nazionalita") or "",
                image_url=row.get("image_url") or "",
            )
        )
        players[row["id"]] = player
        if team is not None:
            EditionRoster.objects.get_or_create(
                edition=edition,
                player=player,
                active_from=LEGACY_START,
                defaults={
                    "team": team,
                    "role": row["ruolo"],
                    "quotazione": row["quotazione"],
                    "quotazione_set_by_admin": True,
                },
            )
        report["players"] += 1

    for row in rows.get("leagues", []):
        admin = users.get(row["admin_id"])
        if admin is None:
            continue
        league, _ = League.objects.get_or_create(
            codice_invito=row["codice_invito"],
            defaults={
                "nome": row["nome"],
                "crediti_iniziali": row["crediti_iniziali"],
                "admin": admin,
                "edition": edition,
                "auction_open": bool(row.get("auction_open")),
                "participant_count": row.get("participant_count"),
            },
        )
        leagues[row["id"]] = league
        report["leagues"] += 1
    for row in rows.get("fanta_teams", []):
        league, owner = leagues.get(row["league_id"]), users.get(row["owner_id"])
        if league is None or owner is None:
            continue
        team, _ = FantaTeam.objects.get_or_create(
            league=league,
            owner=owner,
            defaults={
                "nome": row["nome"],
                "crediti_residui": row["crediti_residui"],
                "punti": row.get("punti") or 0.0,
            },
        )
        fanta[row["id"]] = team
        report["fanta_teams"] += 1
    for row in rows.get("roster_entries", []):
        team, player = fanta.get(row["fanta_team_id"]), players.get(row["lec_player_id"])
        if team and player and not RosterEntry.objects.filter(fanta_team=team, player=player).exists():
            RosterEntry.objects.create(
                fanta_team=team, league=team.league, player=player, crediti_spesi=row["crediti_spesi"]
            )
            report["roster_entries"] += 1

    for row in rows.get("matchdays", []):
        league = leagues.get(row["league_id"])
        if league is None:
            continue
        status = row.get("status") or (MatchdayStatus.CLOSED if row.get("chiusa") else MatchdayStatus.OPEN)
        matchday, _ = Matchday.objects.get_or_create(
            league=league,
            numero=row["numero"],
            defaults={
                "descrizione": row.get("descrizione"),
                "data": row.get("data"),
                "chiusa": bool(row.get("chiusa")),
                "status": status,
                "provisional": False,
            },
        )
        matchdays[row["id"]] = matchday
        report["matchdays"] += 1
    for row in rows.get("player_stats", []):
        matchday, player = matchdays.get(row["matchday_id"]), players.get(row["lec_player_id"])
        if not (matchday and player):
            continue
        PlayerStat.objects.update_or_create(
            matchday=matchday,
            player=player,
            defaults={
                "kills": row.get("kills") or 0,
                "morti": row.get("morti") or 0,
                "assist": row.get("assist") or 0,
                "cs": row.get("cs") or 0,
                "vision_score": row.get("vision_score") or 0,
                "vittoria": bool(row.get("vittoria")),
                "wins": row.get("wins") or (1 if row.get("vittoria") else 0),
                "games_played": max(1, row.get("games_played") or 1),
                "formula_version": row.get("formula_version") or ScoringFormulaVersion.HISTORICAL,
                "fantavoto": row["fantavoto"],
                "source": "MANUAL",
            },
        )
        report["player_stats"] += 1
    for row in rows.get("formations", []):
        team, matchday = fanta.get(row["fanta_team_id"]), matchdays.get(row["matchday_id"])
        if not (team and matchday):
            continue
        formation, _ = Formation.objects.update_or_create(
            fanta_team=team,
            matchday=matchday,
            defaults={
                "source": row.get("source") or "SUBMITTED",
                "confirmed": bool(row.get("confirmed")),
                "punteggio_totale": row.get("punteggio_totale"),
            },
        )
        formations[row["id"]] = formation
        report["formations"] += 1
    for row in rows.get("formation_titolari", []):
        formation, player = formations.get(row["formation_id"]), players.get(row["lec_player_id"])
        if formation and player:
            formation.titolari.add(player)
    for row in rows.get("effective_lineup_periods", []):
        team, player = fanta.get(row["fanta_team_id"]), players.get(row["lec_player_id"])
        if not (team and player):
            continue
        EffectiveLineupPeriod.objects.update_or_create(
            fanta_team=team,
            role=row["role"],
            effective_from=_dt(row["effective_from"]),
            defaults={
                "player": player,
                "effective_until": _dt(row.get("effective_until")),
                "origin": row.get("origin") or "BACKFILL",
            },
        )
        report["lineup_periods"] += 1
    return dict(report)


def read_mysql(url: str) -> dict[str, list[dict]]:  # pragma: no cover - richiede un server MySQL reale
    from urllib.parse import unquote, urlparse

    import pymysql

    parsed = urlparse(url)
    connection = pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=parsed.path.lstrip("/"),
        cursorclass=pymysql.cursors.DictCursor,
    )
    rows: dict[str, list[dict]] = {}
    try:
        with connection.cursor() as cursor:
            for table in TABLES:
                try:
                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows[table] = list(cursor.fetchall())
                except pymysql.err.ProgrammingError:
                    rows[table] = []
    finally:
        connection.close()
    return rows
