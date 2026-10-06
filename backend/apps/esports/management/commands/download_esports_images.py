"""``python manage.py download_esports_images --competition LCK|LPL|LEC|WORLDS``."""

import json

from django.core.management.base import BaseCommand

from apps.esports.images import download_images


class Command(BaseCommand):
    help = "Scarica in MEDIA_ROOT loghi e foto (PandaScore) dei team e dei player della competizione"

    def add_arguments(self, parser):
        parser.add_argument(
            "--competition",
            required=True,
            choices=["LEC", "LCK", "LPL", "WORLDS", "lec", "lck", "lpl", "worlds"],
        )

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(download_images(options["competition"])))
