"""Importa squadre e roster pro da PandaScore.

Serve a popolare LPL/LCK (e le regioni minori qualificate a Worlds) senza
inventare dati: i roster arrivano dal provider, non da costanti nel codice.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ingest.pandascore_client import PandaScoreClient, PandaScoreError, supported_leagues
from teams.models import Competition, PlayerRole, ProPlayer, ProTeam

ROLE_MAP = {
    "top": PlayerRole.TOP, "jun": PlayerRole.JUNGLE, "jungle": PlayerRole.JUNGLE,
    "mid": PlayerRole.MID, "adc": PlayerRole.ADC, "bot": PlayerRole.ADC,
    "sup": PlayerRole.SUPPORT, "support": PlayerRole.SUPPORT,
}

#: Quotazione di partenza per i player importati, quando il provider non
#: fornisce alcun valore economico. Va poi rifinita da Django admin.
DEFAULT_QUOTAZIONE = 50


class Command(BaseCommand):
    help = "Importa squadre e player pro da PandaScore per un competitivo o un torneo."

    def add_arguments(self, parser):
        parser.add_argument("--competition", help="Codice lega presente in SUPPORTED_PRO_LEAGUES")
        parser.add_argument("--tournament-id", type=int, help="Torneo PandaScore (es. una fase Worlds)")
        parser.add_argument("--mark-worlds", action="store_true",
                            help="Marca i player importati come qualificati a Worlds")
        parser.add_argument("--quotazione", type=int, default=DEFAULT_QUOTAZIONE)

    def handle(self, *args, **options):
        client = PandaScoreClient()
        if not client.configured:
            raise CommandError("PANDASCORE_API_TOKEN non configurato")

        tournament_id = options.get("tournament_id")
        competition = (options.get("competition") or "").upper()
        if not tournament_id:
            if not competition:
                raise CommandError("Indica --competition oppure --tournament-id")
            match = next((l for l in supported_leagues() if l.code == competition), None)
            if match is None:
                raise CommandError(
                    f"{competition} non è in SUPPORTED_PRO_LEAGUES: aggiungilo alla configurazione")
            raise CommandError(
                "PandaScore espone i roster per torneo: passa --tournament-id "
                f"del torneo corrente di {competition}")

        try:
            payloads = client.tournament_teams(tournament_id)
        except PandaScoreError as exc:
            raise CommandError(str(exc)) from exc

        competition = competition or Competition.OTHER
        teams, players = self._persist(payloads, competition, options)
        self.stdout.write(self.style.SUCCESS(
            f"Importate {teams} squadre e {players} player ({competition})"))

    @transaction.atomic
    def _persist(self, payloads, competition: str, options) -> tuple[int, int]:
        teams = players = 0
        for payload in payloads:
            team, _ = ProTeam.objects.update_or_create(
                nome=payload.get("name") or payload.get("slug"),
                defaults={
                    "sigla": payload.get("acronym"),
                    "logo_url": payload.get("image_url"),
                    "competition": competition,
                    "pandascore_id": payload.get("id"),
                },
            )
            teams += 1
            for member in payload.get("players", []) or []:
                role = ROLE_MAP.get((member.get("role") or "").strip().lower())
                if role is None:
                    self.stderr.write(
                        f"Ruolo non riconosciuto per {member.get('name')}: saltato")
                    continue
                ProPlayer.objects.update_or_create(
                    nickname=member.get("name"), team=team,
                    defaults={
                        "nome_reale": " ".join(filter(None, [member.get("first_name"),
                                                             member.get("last_name")])) or None,
                        "nazionalita": member.get("nationality"),
                        "image_url": member.get("image_url"),
                        "ruolo": role,
                        "quotazione": options["quotazione"],
                        "competition": competition,
                        "pandascore_id": member.get("id"),
                        "is_worlds_eligible": bool(options["mark_worlds"]),
                    },
                )
                players += 1
        return teams, players
