"""Job in background eseguiti dal processo ``run_scheduler`` (un solo worker, niente Celery)."""

from __future__ import annotations

import functools
import logging

from django.db import close_old_connections, connection

from apps.common.utils import now
from apps.esports.models import Provider, ProviderSyncState

logger = logging.getLogger("apps.scheduler")


def job(func):
    """Isola ogni job: connessioni DB fresche ed eccezioni loggate senza fermare lo scheduler."""

    def refresh_connections():
        # Dentro una transazione (es. nei test) la connessione non va chiusa.
        if not connection.in_atomic_block:
            close_old_connections()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        refresh_connections()
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Job %s fallito", func.__name__)
            return None
        finally:
            refresh_connections()

    return wrapper


@job
def pandascore_sync(competition_code: str | None = None):
    from apps.providers.pandascore.worker import EsportsSyncWorker

    return EsportsSyncWorker().run(competition_code, discover=competition_code is None)


@job
def leaguepedia_enrich(competition=None, limit: int | None = None):
    from apps.providers.leaguepedia.worker import LeaguepediaEnrichWorker

    return LeaguepediaEnrichWorker().run(competition, limit=limit)


@job
def auction_sweeper():
    from apps.leagues.auctions import finalize_expired

    return finalize_expired()


@job
def matchdays_maintenance():
    from apps.lineups.services import backfill_all
    from apps.matchdays.services import auto_close_matchdays
    from apps.worlds.services import refresh_all_worlds_matchdays

    refreshed = refresh_all_worlds_matchdays()
    backfilled = backfill_all()
    return {"worlds_leagues": refreshed, "backfilled": backfilled, **auto_close_matchdays()}


@job
def manual_sync_requests():
    """Esegue le sincronizzazioni richieste dall'admin con ``POST /api/admin/competitions/{code}/synchronize``."""
    from apps.providers.leaguepedia.worker import LeaguepediaEnrichWorker
    from apps.providers.pandascore.worker import EsportsSyncWorker

    handled = []
    pending = ProviderSyncState.objects.filter(sync_requested_at__isnull=False).select_related("competition")
    for state in pending:
        competition = state.competition
        ProviderSyncState.objects.filter(pk=state.pk).update(sync_requested_at=None)
        try:
            if state.provider == Provider.PANDASCORE:
                EsportsSyncWorker().run(competition.code if competition else None)
            else:
                LeaguepediaEnrichWorker().run(competition, limit=3)
        except Exception:
            logger.exception("Sincronizzazione manuale %s fallita", state.provider)
        handled.append((state.provider, competition.code if competition else None, now()))
    return handled
