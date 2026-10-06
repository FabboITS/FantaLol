"""Crea l'account amministratore globale a partire dalle variabili d'ambiente.

Sostituisce ``AdminAccountInitializer``: nessuna credenziale è salvata nel repository.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.users.models import Role, User


class Command(BaseCommand):
    help = "Crea (se assente) l'admin globale da ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD"

    def handle(self, *args, **options):
        username = settings.ADMIN_USERNAME
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD
        if not (username and email and password):
            self.stderr.write(
                self.style.WARNING(
                    "ADMIN_USERNAME, ADMIN_EMAIL o ADMIN_PASSWORD non impostate: nessun admin creato"
                )
            )
            return
        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_user(username=username, email=email, password=password, role=Role.ADMIN)
            self.stdout.write(self.style.SUCCESS(f"Admin globale '{username}' creato"))
            return
        if user.role != Role.ADMIN:
            user.role = Role.ADMIN
            user.save(update_fields=["role", "is_staff"])
            self.stdout.write(self.style.SUCCESS(f"Utente '{username}' promosso ad ADMIN"))
        else:
            self.stdout.write(f"Admin globale '{username}' già presente")
