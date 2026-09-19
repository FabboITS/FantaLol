"""Svuota le utenze tenendo solo l'admin globale.

Cancellando un utente cadono a cascata le sue leghe, i suoi FantaTeam, le rose,
le formazioni e lo storico di titolarità: è quindi un reset completo del gioco,
non solo della tabella utenti. I dati pro (squadre, player, serie, box score)
non vengono toccati.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User

ADMIN_USERNAME = "Natsu_Admin"


class Command(BaseCommand):
    help = "Cancella tutti gli utenti tranne l'admin globale (e i dati collegati)."

    def add_arguments(self, parser):
        parser.add_argument("--keep", default=ADMIN_USERNAME,
                            help=f"Username da preservare (default: {ADMIN_USERNAME})")
        parser.add_argument("--dry-run", action="store_true",
                            help="Elenca cosa verrebbe cancellato, senza cancellare")
        parser.add_argument("--yes", action="store_true",
                            help="Non chiedere conferma interattiva")

    @transaction.atomic
    def handle(self, *args, **options):
        keep = options["keep"]
        doomed = User.objects.exclude(username=keep).order_by("username")
        usernames = list(doomed.values_list("username", flat=True))

        if not usernames:
            self.stdout.write(self.style.SUCCESS(
                f"Nessun utente da cancellare: resta solo {keep}"))
            return

        self.stdout.write(f"Utenti da cancellare ({len(usernames)}): {', '.join(usernames)}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: nessuna cancellazione effettuata"))
            return
        if not options["yes"]:
            answer = input(f"Confermi la cancellazione di {len(usernames)} utenti? [s/N] ")
            if answer.strip().lower() not in {"s", "si", "sì", "y", "yes"}:
                self.stdout.write(self.style.WARNING("Annullato"))
                return

        deleted, _ = doomed.delete()
        self.stdout.write(self.style.SUCCESS(f"Cancellate {deleted} righe collegate"))

        admin = User.objects.filter(username=keep).first()
        if admin is None:
            self.stdout.write(self.style.WARNING(
                f"Attenzione: l'utente {keep} non esiste. Esegui `seed_base_data`."))
        elif admin.role != Role.ADMIN:
            self.stdout.write(self.style.WARNING(f"Attenzione: {keep} non ha ruolo ADMIN"))
