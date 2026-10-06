"""Ricava l'ID PandaScore della lega WORLDS (``GET /lol/leagues?search[name]=World Championship``)."""

from django.core.management.base import BaseCommand

from apps.competitions.models import Competition
from apps.providers.pandascore.worker import EsportsSyncWorker


class Command(BaseCommand):
    help = "Risolve gli ID PandaScore mancanti delle competizioni (WORLDS)"

    def handle(self, *args, **options):
        worker = EsportsSyncWorker()
        for competition in Competition.objects.filter(pandascore_league_id__isnull=True):
            league_id = worker.resolve_league_id(competition)
            self.stdout.write(f"{competition.code}: {league_id or 'non trovato'}")
