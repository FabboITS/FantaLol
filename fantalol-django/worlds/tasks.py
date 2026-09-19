"""Task Celery della modalità Worlds."""
from __future__ import annotations

from celery import shared_task


@shared_task(name="worlds.tasks.lock_due_stage_lineups")
def lock_due_stage_lineups() -> int:
    """Blocca le formazioni delle fasi la cui deadline è scaduta."""
    from .services import lock_due_stage_lineups as run

    return run()


@shared_task(name="worlds.tasks.finalize_expired_worlds_auctions")
def finalize_expired_worlds_auctions() -> int:
    from .services import finalize_expired_auctions

    return finalize_expired_auctions()
