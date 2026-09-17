"""Configurazione Celery: sostituisce gli `@Scheduled` di Spring."""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("fantalol")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Calendario/stato/risultati serie: ogni ora (ex worker Spring @Scheduled).
    "sync-pandascore-hourly": {
        "task": "ingest.tasks.sync_pandascore",
        "schedule": crontab(minute=15),
    },
    # Box score Leaguepedia: ogni 30 minuti, a batch limitati.
    "enrich-leaguepedia-half-hourly": {
        "task": "ingest.tasks.enrich_leaguepedia",
        "schedule": crontab(minute="0,30"),
    },
    # Chiusura della finestra formazioni: venerdì 00:00 Europe/Rome.
    # In UTC cade alle 22:00 del giovedì (CEST) / 23:00 (CET): giriamo ogni
    # ora e lasciamo al task la verifica del fuso applicativo.
    "apply-lineup-windows": {
        "task": "lineups.tasks.apply_due_lineup_windows",
        "schedule": crontab(minute=5),
    },
    # Chiusura aste scadute (ex @Scheduled(fixedDelay = 500)).
    "finalize-expired-auctions": {
        "task": "leagues.tasks.finalize_expired_auctions",
        "schedule": 5.0,
    },
    # Deadline formazione per fase Worlds.
    "lock-worlds-stage-lineups": {
        "task": "worlds.tasks.lock_due_stage_lineups",
        "schedule": crontab(minute="*/10"),
    },
    # Chiusura aste scadute nelle leghe Worlds.
    "finalize-expired-worlds-auctions": {
        "task": "worlds.tasks.finalize_expired_worlds_auctions",
        "schedule": 5.0,
    },
}
