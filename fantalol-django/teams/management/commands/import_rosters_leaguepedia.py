"""Importa squadre e roster pro da Leaguepedia (Cargo API).

È la stessa fonte che l'ingest usa per i box score, quindi i nomi arrivano già
nella forma canonica che `PlayerAlias`/`TeamAlias` si aspettano: meno mismatch
da correggere a mano.

Le query Cargo di lettura non richiedono credenziali bot.

    python manage.py import_rosters_leaguepedia --competition LPL
    python manage.py import_rosters_leaguepedia --competition LCK
    python manage.py import_rosters_leaguepedia --competition LEC --dry-run

I dati Leaguepedia sono distribuiti con licenza CC BY-SA 3.0.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ingest.leaguepedia_client import LeaguepediaClient, LeaguepediaError
from teams.models import Competition, PlayerRole, ProPlayer, ProTeam

#: Regione Leaguepedia di ciascun competitivo supportato.
DEFAULT_REGIONS = {
    Competition.LEC.value: "Europe",
    Competition.LPL.value: "China",
    Competition.LCK.value: "Korea",
    Competition.LCS.value: "North America",
    Competition.LTA.value: "North America",
    Competition.PCS.value: "Taiwan",
    Competition.VCS.value: "Vietnam",
    Competition.CBLOL.value: "Brazil",
}

ROLE_MAP = {
    "top": PlayerRole.TOP.value,
    "jungle": PlayerRole.JUNGLE.value,
    "jungler": PlayerRole.JUNGLE.value,
    "mid": PlayerRole.MID.value,
    "middle": PlayerRole.MID.value,
    "bot": PlayerRole.ADC.value,
    "adc": PlayerRole.ADC.value,
    "ad carry": PlayerRole.ADC.value,
    "support": PlayerRole.SUPPORT.value,
}

#: Quotazione di partenza: il provider non espone alcun valore economico, la
#: si rifinisce poi da Django admin o con --quotazione.
DEFAULT_QUOTAZIONE = 50

TEAM_FIELDS = "T.Name, T.Short, T.Region, T.Image, T.IsDisbanded"
PLAYER_FIELDS = "P.ID, P.Player, P.Country, P.Role, P.Team, P.Image, P.IsRetired"


class Command(BaseCommand):
    help = "Importa squadre e player pro di un competitivo da Leaguepedia."

    def add_arguments(self, parser):
        parser.add_argument("--competition", required=True,
                            help="Codice competitivo (LEC, LPL, LCK, ...)")
        parser.add_argument("--region", default=None,
                            help="Regione Leaguepedia; se assente si deduce dal competitivo")
        parser.add_argument("--quotazione", type=int, default=DEFAULT_QUOTAZIONE,
                            help=f"Quotazione base assegnata ai player (default {DEFAULT_QUOTAZIONE})")
        parser.add_argument("--mark-worlds", action="store_true",
                            help="Marca i player importati come qualificati a Worlds")
        parser.add_argument("--dry-run", action="store_true",
                            help="Mostra cosa verrebbe importato, senza scrivere")

    def handle(self, *args, **options):
        competition = options["competition"].upper()
        valid = {choice.value for choice in Competition}
        if competition not in valid:
            raise CommandError(
                f"Competitivo sconosciuto: {competition}. Validi: {', '.join(sorted(valid))}")

        region = options["region"] or DEFAULT_REGIONS.get(competition)
        if not region:
            raise CommandError(
                f"Nessuna regione nota per {competition}: passala con --region")

        client = LeaguepediaClient()
        try:
            teams = self._fetch_teams(client, region)
        except LeaguepediaError as exc:
            raise CommandError(f"Leaguepedia non raggiungibile: {exc}") from exc

        if not teams:
            raise CommandError(f"Nessuna squadra trovata per la regione {region}")

        self.stdout.write(f"{competition} ({region}): {len(teams)} squadre trovate")

        rosters: list[tuple[dict, list[dict]]] = []
        for team in teams:
            try:
                players = self._fetch_players(client, team["Name"])
            except LeaguepediaError as exc:
                self.stderr.write(f"  {team['Name']}: roster non recuperato ({exc})")
                continue
            rosters.append((team, players))
            roles = ", ".join(f"{p['ID']} ({p['Role']})" for p in players) or "nessun player"
            self.stdout.write(f"  {team['Name']}: {roles}")

        if options["dry_run"]:
            total = sum(len(players) for _, players in rosters)
            self.stdout.write(self.style.WARNING(
                f"Dry run: {len(rosters)} squadre e {total} player NON importati"))
            return

        teams_saved, players_saved, skipped = self._persist(rosters, competition, options)
        if skipped:
            self.stderr.write(f"{skipped} player saltati (ruolo non riconosciuto o vuoto)")
        self.stdout.write(self.style.SUCCESS(
            f"Importate {teams_saved} squadre e {players_saved} player ({competition}). "
            f"Dati Leaguepedia, licenza CC BY-SA 3.0."))

    # --- lettura ----------------------------------------------------------
    def _fetch_teams(self, client: LeaguepediaClient, region: str) -> list[dict]:
        rows = client.cargo_query(
            tables="Teams=T",
            fields=TEAM_FIELDS,
            where=f"T.Region='{self._escape(region)}'",
            order_by="T.Name ASC",
        )
        return [row for row in rows if row.get("Name") and not self._yes(row.get("IsDisbanded"))]

    def _fetch_players(self, client: LeaguepediaClient, team_name: str) -> list[dict]:
        rows = client.cargo_query(
            tables="Players=P",
            fields=PLAYER_FIELDS,
            where=f"P.Team='{self._escape(team_name)}'",
            order_by="P.ID ASC",
        )
        return [row for row in rows if row.get("ID") and not self._yes(row.get("IsRetired"))]

    # --- scrittura --------------------------------------------------------
    @transaction.atomic
    def _persist(self, rosters, competition: str, options) -> tuple[int, int, int]:
        teams_saved = players_saved = skipped = 0
        for team_row, player_rows in rosters:
            team, _ = ProTeam.objects.update_or_create(
                nome=team_row["Name"],
                defaults={
                    "sigla": (team_row.get("Short") or "")[:10] or None,
                    "logo_url": team_row.get("Image") or None,
                    "competition": competition,
                    # Il nome canonico è già quello di Leaguepedia: l'ingest
                    # aggancia i box score senza bisogno di un alias.
                    "leaguepedia_name": team_row["Name"],
                },
            )
            teams_saved += 1

            for row in player_rows:
                role = ROLE_MAP.get((row.get("Role") or "").strip().lower())
                if role is None:
                    skipped += 1
                    continue
                ProPlayer.objects.update_or_create(
                    nickname=row["ID"], team=team,
                    defaults={
                        "nome_reale": row.get("Player") or None,
                        "nazionalita": row.get("Country") or None,
                        "image_url": row.get("Image") or None,
                        "ruolo": role,
                        "quotazione": options["quotazione"],
                        "competition": competition,
                        "leaguepedia_link": row["ID"],
                        "is_worlds_eligible": bool(options["mark_worlds"]),
                    },
                )
                players_saved += 1
        return teams_saved, players_saved, skipped

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("'", "\\'")

    @staticmethod
    def _yes(value) -> bool:
        return str(value).strip().lower() in {"yes", "1", "true"}
