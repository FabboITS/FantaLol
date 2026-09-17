"""Travaso dal vecchio schema MySQL/JPA al nuovo schema Postgres/Django.

Preserva gli **id** di utenti, leghe, FantaTeam e rose, così i riferimenti già
presenti lato frontend restano validi. Richiede accesso in lettura al DB legacy
(`--mysql-url`), altrimenti non fa nulla: senza DB di origine si parte dalle
migration vuote più `seed_base_data`.

Uso:
    python manage.py migrate_from_legacy \\
        --mysql-url mysql://user:pass@host:3306/fantalol [--dry-run]
"""
from __future__ import annotations

from urllib.parse import unquote, urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from accounts.models import Role, User, UserProfile
from leagues.models import FantaTeam, League, RosterEntry
from lineups.models import LineupPeriod, LineupPeriodOrigin
from teams.models import Competition, ProPlayer, ProTeam


class Command(BaseCommand):
    help = "Importa utenti, leghe, FantaTeam, rose e storico formazioni dal DB legacy MySQL."

    def add_arguments(self, parser):
        parser.add_argument("--mysql-url", required=True,
                            help="mysql://utente:password@host:porta/database")
        parser.add_argument("--dry-run", action="store_true",
                            help="Mostra solo quante righe verrebbero importate")

    def handle(self, *args, **options):
        try:
            import pymysql  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise CommandError(
                "Serve PyMySQL per leggere il DB legacy: pip install PyMySQL") from exc

        parsed = urlparse(options["mysql_url"])
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise CommandError("L'URL deve iniziare per mysql://")
        legacy = pymysql.connect(
            host=parsed.hostname, port=parsed.port or 3306,
            user=unquote(parsed.username or ""), password=unquote(parsed.password or ""),
            database=(parsed.path or "/").lstrip("/"), cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            counts = self._migrate(legacy, dry_run=options["dry_run"])
        finally:
            legacy.close()

        for label, value in counts.items():
            self.stdout.write(f"{label}: {value}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: nessuna scrittura effettuata"))
        else:
            self.stdout.write(self.style.SUCCESS("Migrazione completata"))

    def _rows(self, legacy, query: str) -> list[dict]:
        with legacy.cursor() as cursor:
            cursor.execute(query)
            return list(cursor.fetchall())

    @transaction.atomic
    def _migrate(self, legacy, *, dry_run: bool) -> dict[str, int]:
        counts: dict[str, int] = {}

        users = self._rows(legacy, "SELECT * FROM users")
        counts["utenti"] = len(users)
        if not dry_run:
            for row in users:
                User.objects.update_or_create(
                    id=row["id"],
                    defaults={
                        "username": row["username"],
                        "email": row["email"],
                        # L'hash BCrypt legacy è riusabile con BCryptPasswordHasher.
                        "password": row["password"] if str(row["password"]).startswith("bcrypt$")
                        else f"bcrypt${row['password']}",
                        "role": row.get("role") or Role.USER,
                        "enabled": bool(row.get("enabled", True)),
                        "is_staff": (row.get("role") == Role.ADMIN),
                        "is_superuser": (row.get("role") == Role.ADMIN),
                    },
                )

        profiles = self._rows(legacy, "SELECT * FROM user_profiles")
        counts["profili"] = len(profiles)
        if not dry_run:
            for row in profiles:
                UserProfile.objects.update_or_create(
                    id=row["id"],
                    defaults={
                        "user_id": row["user_id"],
                        "nome_visualizzato": row.get("nome_visualizzato"),
                        "bio": row.get("bio"),
                        "avatar_url": row.get("avatar_url"),
                        "summoner_name": row.get("summoner_name"),
                    },
                )

        teams = self._rows(legacy, "SELECT * FROM lec_teams")
        counts["squadre_pro"] = len(teams)
        if not dry_run:
            for row in teams:
                ProTeam.objects.update_or_create(
                    id=row["id"],
                    defaults={"nome": row["nome"], "sigla": row.get("sigla"),
                              "logo_url": row.get("logo_url"), "competition": Competition.LEC},
                )

        players = self._rows(legacy, "SELECT * FROM lec_players")
        counts["player_pro"] = len(players)
        if not dry_run:
            for row in players:
                ProPlayer.objects.update_or_create(
                    id=row["id"],
                    defaults={
                        "nickname": row["nickname"], "nome_reale": row.get("nome_reale"),
                        "nazionalita": row.get("nazionalita"), "image_url": row.get("image_url"),
                        "ruolo": row["ruolo"], "quotazione": row["quotazione"],
                        "team_id": row["team_id"], "competition": Competition.LEC,
                        "leaguepedia_link": row.get("oracle_player_id"),
                    },
                )

        leagues = self._rows(legacy, "SELECT * FROM leagues")
        counts["leghe"] = len(leagues)
        if not dry_run:
            for row in leagues:
                League.objects.update_or_create(
                    id=row["id"],
                    defaults={
                        "nome": row["nome"], "codice_invito": row["codice_invito"],
                        "crediti_iniziali": row["crediti_iniziali"], "admin_id": row["admin_id"],
                        "auction_open": bool(row.get("auction_open")),
                        "participant_count": row.get("participant_count"),
                        "competition": Competition.LEC,
                    },
                )

        fanta_teams = self._rows(legacy, "SELECT * FROM fanta_teams")
        counts["fanta_team"] = len(fanta_teams)
        if not dry_run:
            for row in fanta_teams:
                FantaTeam.objects.update_or_create(
                    id=row["id"],
                    defaults={"nome": row["nome"], "crediti_residui": row["crediti_residui"],
                              "league_id": row["league_id"], "owner_id": row["owner_id"],
                              "punti": row.get("punti") or 0.0},
                )

        roster = self._rows(legacy, "SELECT * FROM roster_entries")
        counts["rose"] = len(roster)
        if not dry_run:
            for row in roster:
                RosterEntry.objects.update_or_create(
                    id=row["id"],
                    defaults={"fanta_team_id": row["fanta_team_id"],
                              "player_id": row["lec_player_id"],
                              "crediti_spesi": row["crediti_spesi"]},
                )

        periods = self._rows(legacy, "SELECT * FROM effective_lineup_periods")
        counts["storico_formazioni"] = len(periods)
        if not dry_run:
            for row in periods:
                LineupPeriod.objects.update_or_create(
                    id=row["id"],
                    defaults={
                        "fanta_team_id": row["fanta_team_id"], "role": row["role"],
                        "player_id": row["lec_player_id"],
                        "valid_from": row["effective_from"], "valid_to": row.get("effective_until"),
                        "origin": row.get("origin") or LineupPeriodOrigin.BACKFILL,
                    },
                )

        if not dry_run:
            self._reset_sequences()
        return counts

    def _reset_sequences(self) -> None:
        """Riallinea le sequenze Postgres dopo un import a id espliciti."""
        if connection.vendor != "postgresql":
            return
        tables = ["users", "user_profiles", "pro_teams", "pro_players", "leagues",
                  "fanta_teams", "roster_entries", "lineup_periods"]
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                    "COALESCE((SELECT MAX(id) FROM " + connection.ops.quote_name(table) + "), 1))",
                    [table],
                )
