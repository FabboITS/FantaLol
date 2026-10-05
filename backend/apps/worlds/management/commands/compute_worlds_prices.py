"""``python manage.py compute_worlds_prices [--edition ID] [--force]``."""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.competitions.models import CompetitionEdition
from apps.worlds.pricing import compute_prices


class Command(BaseCommand):
    help = "Calcola le quotazioni iniziali (5–20) del listone Worlds dalla stagione regionale"

    def add_arguments(self, parser):
        parser.add_argument("--edition", type=int, help="ID dell'edizione WORLDS (default: la più recente)")
        parser.add_argument("--force", action="store_true", help="Sovrascrive anche le quotazioni dell'admin")

    def handle(self, *args, **options):
        qs = CompetitionEdition.objects.filter(competition__code="WORLDS")
        edition = (
            qs.filter(pk=options["edition"]).first()
            if options.get("edition")
            else qs.order_by("-starts_at").first()
        )
        if edition is None:
            raise CommandError("Nessuna edizione WORLDS trovata")
        self.stdout.write(json.dumps(compute_prices(edition, force=options["force"])))
