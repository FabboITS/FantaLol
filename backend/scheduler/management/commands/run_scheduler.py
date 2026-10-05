"""Processo scheduler: ``python manage.py run_scheduler``.

Un solo processo attivo grazie a un lock advisory PostgreSQL (``pg_try_advisory_lock``): un secondo
scheduler resta in attesa finché il primo non termina.
"""

import logging
import time

import psycopg
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.core.management.base import BaseCommand

from scheduler import jobs

logger = logging.getLogger("apps.scheduler")
ADVISORY_LOCK_KEY = 4_242_2026


def _dsn() -> str:
    db = settings.DATABASES["default"]
    return psycopg.conninfo.make_conninfo(
        dbname=db["NAME"],
        user=db.get("USER") or None,
        password=db.get("PASSWORD") or None,
        host=db.get("HOST") or None,
        port=db.get("PORT") or None,
    )


def acquire_lock(wait_seconds: float = 30.0, attempts: int | None = None):
    """Ritorna la connessione che detiene il lock (va tenuta aperta per tutta la vita del processo)."""
    tried = 0
    while True:
        connection = psycopg.connect(_dsn(), autocommit=True)
        acquired = connection.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK_KEY,)).fetchone()[0]
        if acquired:
            return connection
        connection.close()
        tried += 1
        if attempts is not None and tried >= attempts:
            return None
        logger.warning("Un altro scheduler è attivo: nuovo tentativo tra %ss", wait_seconds)
        time.sleep(wait_seconds)


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC", job_defaults={"coalesce": True, "max_instances": 1})
    scheduler.add_job(
        jobs.pandascore_sync, "interval", minutes=60, id="pandascore_sync", next_run_time=_now()
    )
    scheduler.add_job(
        jobs.leaguepedia_enrich, "interval", minutes=30, id="leaguepedia_enrich", next_run_time=_now()
    )
    scheduler.add_job(jobs.auction_sweeper, "interval", seconds=1, id="auction_sweeper")
    scheduler.add_job(jobs.matchdays_maintenance, "interval", minutes=5, id="matchdays_maintenance")
    scheduler.add_job(jobs.manual_sync_requests, "interval", seconds=15, id="manual_sync_requests")
    return scheduler


def _now():
    from django.utils import timezone

    return timezone.now()


class Command(BaseCommand):
    help = "Avvia i job in background (sync PandaScore, arricchimento Leaguepedia, aste, giornate)"

    def handle(self, *args, **options):
        lock = acquire_lock()
        logger.info("Lock advisory acquisito: avvio dello scheduler")
        if not settings.PANDASCORE_API_TOKEN:
            logger.warning("PANDASCORE_API_TOKEN assente: il sync PandaScore non verrà eseguito")
        if not (settings.LEAGUEPEDIA_BOT_USERNAME and settings.LEAGUEPEDIA_BOT_PASSWORD):
            logger.warning("Bot password Leaguepedia assente: l'arricchimento non verrà eseguito")
        try:
            build_scheduler().start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler arrestato")
        finally:
            lock.close()
