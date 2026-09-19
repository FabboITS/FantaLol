"""Task Celery dell'ingest (ex worker Spring `@Scheduled`)."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="ingest.tasks.sync_pandascore")
def sync_pandascore() -> dict:
    """Ogni ora: calendario, stato e risultati delle serie delle leghe allowlist."""
    from .services import sync_pandascore as run

    report = run()
    logger.info("sync_pandascore: +%s ~%s !%s", report.inserted, report.updated, report.failed)
    return {"inserted": report.inserted, "updated": report.updated,
            "failed": report.failed, "skipped": report.skipped}


@shared_task(name="ingest.tasks.enrich_leaguepedia")
def enrich_leaguepedia(limit: int | None = None) -> dict:
    """Ogni 30 minuti: box score Leaguepedia + ricalcolo fantapunti."""
    from .services import enrich_leaguepedia as run

    report = run(limit=limit)
    logger.info("enrich_leaguepedia: +%s ~%s !%s", report.inserted, report.updated, report.failed)
    return {"inserted": report.inserted, "updated": report.updated,
            "failed": report.failed, "skipped": report.skipped}
