"""Task Celery delle leghe (ex `@Scheduled` di `AuctionService`)."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="leagues.tasks.finalize_expired_auctions")
def finalize_expired_auctions() -> int:
    from . import services

    finalized = services.finalize_expired_auctions()
    if finalized:
        logger.info("Aste concluse: %s", finalized)
    return finalized
