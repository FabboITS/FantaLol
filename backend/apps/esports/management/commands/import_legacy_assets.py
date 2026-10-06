"""``python manage.py import_legacy_assets [--source frontend/]``: migra gli asset LEC dell'originale."""

import json

from django.core.management.base import BaseCommand

from apps.esports.images import import_legacy_assets


class Command(BaseCommand):
    help = "Copia in MEDIA_ROOT i loghi (assets/team-logos) e le foto per ruolo (Player_immage/) esistenti"

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Cartella del frontend originale (default: FRONTEND_DIR)")

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(import_legacy_assets(options.get("source"))))
