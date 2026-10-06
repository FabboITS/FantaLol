"""Arricchimento manuale da Leaguepedia: ``python manage.py enrich_leaguepedia --competition LPL``."""

import json

from django.core.management.base import BaseCommand

from apps.competitions.models import Competition
from apps.providers.leaguepedia.worker import LeaguepediaEnrichWorker


class Command(BaseCommand):
    help = "Scarica da Leaguepedia le statistiche per game delle serie concluse"

    def add_arguments(self, parser):
        parser.add_argument("--competition")
        parser.add_argument("--limit", type=int)

    def handle(self, *args, **options):
        competition = None
        if options.get("competition"):
            competition = Competition.objects.get(code__iexact=options["competition"])
        report = LeaguepediaEnrichWorker().run(competition, limit=options.get("limit"))
        self.stdout.write(json.dumps(report, indent=2, default=str))
