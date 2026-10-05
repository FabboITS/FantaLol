"""Sincronizzazione manuale PandaScore: ``python manage.py sync_pandascore --competition LCK``."""

import json

from django.core.management.base import BaseCommand

from apps.providers.pandascore.worker import EsportsSyncWorker


class Command(BaseCommand):
    help = "Sincronizza calendario, risultati e roster da PandaScore"

    def add_arguments(self, parser):
        parser.add_argument("--competition", help="LEC, LCK, LPL o WORLDS (default: tutte)")
        parser.add_argument(
            "--discover",
            action="store_true",
            help="Crea/aggiorna le edizioni a partire dalle serie PandaScore",
        )

    def handle(self, *args, **options):
        report = EsportsSyncWorker().run(options.get("competition"), discover=options["discover"])
        self.stdout.write(json.dumps(report, indent=2, default=str))
