"""``python manage.py migrate_from_mysql --mysql-url mysql://user:pass@host:3306/fantalol``.

Richiede l'extra opzionale ``pip install ".[mysql]"`` (PyMySQL). Idempotente, con report finale.
"""

import json

from django.core.management.base import BaseCommand

from apps.users.legacy_import import import_rows, read_mysql


class Command(BaseCommand):
    help = "Importa utenti, leghe, rose, giornate e punteggi dal database MySQL del backend Java"

    def add_arguments(self, parser):
        parser.add_argument("--mysql-url", required=True)

    def handle(self, *args, **options):
        report = import_rows(read_mysql(options["mysql_url"]))
        self.stdout.write(json.dumps(report, indent=2))
