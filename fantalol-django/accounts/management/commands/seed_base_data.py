"""Seed iniziale: admin globale + roster pro.

È l'unico punto in cui vengono creati utenti: il seed **non** crea account di
prova. Ogni altra utenza nasce dalla registrazione via API.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User
from teams.models import Competition, ProPlayer, ProTeam
from teams.seed_data import LEC_TEAMS, player_image_url, team_logo_url

ADMIN_USERNAME = "Natsu_Admin"
ADMIN_EMAIL = "natsu-admin@fantalol.local"

#: Hash BCrypt della password dell'admin globale, usato quando non è impostata
#: la variabile d'ambiente `DJANGO_ADMIN_PASSWORD`. È un hash, non la password
#: in chiaro, ma resta comunque materiale sensibile versionato: in produzione
#: imposta `DJANGO_ADMIN_PASSWORD` e ruota la credenziale.
ADMIN_PASSWORD_HASH = "$2b$12$D766vfUCNMuSbCF45Jt3puB5kGj.2z8LDXK.yDDDw2v1R6wT6C8Am"


class Command(BaseCommand):
    help = "Crea l'admin globale e i roster pro iniziali (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", default=None,
                            help="Password in chiaro per l'admin "
                                 "(default: DJANGO_ADMIN_PASSWORD, poi l'hash di default)")
        parser.add_argument("--rosters", default=None,
                            help="JSON con roster aggiuntivi: "
                                 "{\"LPL\": [[nome, sigla, [[nick, ruolo, naz, quot]]]]}")
        parser.add_argument("--skip-teams", action="store_true", help="Crea solo l'admin")
        parser.add_argument("--reset-admin-password", action="store_true",
                            help="Reimposta la password anche se l'admin esiste già")

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_admin(options["admin_password"], options["reset_admin_password"])
        if options["skip_teams"]:
            return
        created = self._seed_competition(Competition.LEC, LEC_TEAMS)
        if options["rosters"]:
            payload = json.loads(Path(options["rosters"]).read_text(encoding="utf-8"))
            for competition, teams in payload.items():
                created += self._seed_competition(competition.upper(), teams)
        self.stdout.write(self.style.SUCCESS(f"Seed completato: {created} player creati/aggiornati"))

    def _seed_admin(self, plain_password: str | None, reset_password: bool) -> None:
        admin, created = User.objects.get_or_create(
            username=ADMIN_USERNAME,
            defaults={"email": ADMIN_EMAIL, "role": Role.ADMIN, "enabled": True,
                      "is_staff": True, "is_superuser": True},
        )
        plain_password = plain_password or settings.FANTALOL.get("ADMIN_PASSWORD")
        if plain_password and (created or reset_password):
            admin.set_password(plain_password)
        elif created:
            # L'hash BCrypt viene riusato tale e quale: gli basta il prefisso
            # con cui Django identifica l'hasher (`BCryptPasswordHasher`).
            admin.password = f"bcrypt${ADMIN_PASSWORD_HASH}"
        admin.role = Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        self.stdout.write(f"Admin globale: {ADMIN_USERNAME} ({'creato' if created else 'già presente'})")

    def _seed_competition(self, competition: str, teams) -> int:
        count = 0
        for nome, sigla, roster in teams:
            team, _ = ProTeam.objects.update_or_create(
                nome=nome,
                defaults={"sigla": sigla, "logo_url": team_logo_url(nome),
                          "competition": competition},
            )
            for nickname, ruolo, nazionalita, quotazione in roster:
                ProPlayer.objects.update_or_create(
                    nickname=nickname, team=team,
                    defaults={
                        "ruolo": ruolo,
                        "nazionalita": nazionalita,
                        "quotazione": quotazione,
                        "competition": competition,
                        "image_url": player_image_url(nickname, ruolo),
                    },
                )
                count += 1
        self.stdout.write(f"{competition}: {len(teams)} squadre, {count} player")
        return count
