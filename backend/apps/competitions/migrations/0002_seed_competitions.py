"""Seed delle competizioni e delle politiche di formazione di default.

Gli ID PandaScore di LEC (4197), LCK (293) e LPL (294) sono quelli verificati nel prompt di progetto.
L'ID della lega WORLDS NON viene indovinato: si ricava con ``python manage.py resolve_pandascore_leagues``
(``GET /lol/leagues?search[name]=World Championship``), vedi docs/adr/0004.
"""

from django.db import migrations

COMPETITIONS = [
    {"code": "LEC", "name": "LoL EMEA Championship", "region": "EMEA", "ruleset": "REGIONAL",
     "timezone": "Europe/Rome", "pandascore_league_id": 4197, "leaguepedia_name": "LEC", "display_order": 1},
    {"code": "LCK", "name": "LoL Champions Korea", "region": "Corea", "ruleset": "REGIONAL",
     "timezone": "Asia/Seoul", "pandascore_league_id": 293, "leaguepedia_name": "LCK", "display_order": 2},
    {"code": "LPL", "name": "LoL Pro League", "region": "Cina", "ruleset": "REGIONAL",
     "timezone": "Asia/Shanghai", "pandascore_league_id": 294, "leaguepedia_name": "LPL", "display_order": 3},
    {"code": "WORLDS", "name": "World Championship", "region": "Internazionale", "ruleset": "WORLDS",
     "timezone": "Europe/Rome", "pandascore_league_id": None, "leaguepedia_name": "Worlds",
     "display_order": 4},
]

POLICIES = [
    {"name": "LEC settimanale (mar–gio, effettiva ven)", "strategy": "FIXED_WEEKLY_WINDOW", "open_day": 2,
     "close_day": 4, "effective_day": 5, "timezone": "Europe/Rome", "lock_minutes": 60},
    {"name": "Blocco 60 minuti prima della prima serie", "strategy": "LOCK_BEFORE_FIRST_MATCH", "open_day": 2,
     "close_day": 4, "effective_day": 5, "timezone": "", "lock_minutes": 60},
]


def seed(apps, schema_editor):
    Competition = apps.get_model("competitions", "Competition")
    LineupPolicy = apps.get_model("competitions", "LineupPolicy")
    for values in COMPETITIONS:
        Competition.objects.update_or_create(code=values["code"], defaults=values)
    for values in POLICIES:
        LineupPolicy.objects.update_or_create(name=values["name"], defaults=values)


def unseed(apps, schema_editor):
    apps.get_model("competitions", "Competition").objects.filter(
        code__in=[c["code"] for c in COMPETITIONS], editions__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("competitions", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
