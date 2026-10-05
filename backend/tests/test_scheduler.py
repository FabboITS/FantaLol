"""Scheduler: lock advisory, job isolati, richieste di sync manuali, comandi di gestione."""

import json

import pytest
import respx
from django.core.management import call_command

from apps.competitions.models import Competition
from apps.esports.models import ProviderSyncState
from scheduler import jobs
from scheduler.management.commands.run_scheduler import acquire_lock, build_scheduler

from .pipeline_helpers import cargo_router, lck_edition, mock_lck


@pytest.mark.django_db(transaction=True)
def test_lock_advisory_consente_un_solo_scheduler():
    first = acquire_lock(attempts=1)
    assert first is not None
    assert acquire_lock(wait_seconds=0, attempts=1) is None
    first.close()
    again = acquire_lock(attempts=1)
    assert again is not None
    again.close()


def test_registrazione_dei_job():
    ids = {j.id for j in build_scheduler().get_jobs()}
    assert ids == {"pandascore_sync", "leaguepedia_enrich", "auction_sweeper", "matchdays_maintenance",
                   "manual_sync_requests"}


@pytest.mark.django_db
def test_job_che_fallisce_non_ferma_lo_scheduler(monkeypatch, caplog):
    def boom():
        raise RuntimeError("esploso")

    wrapped = jobs.job(boom)
    assert wrapped() is None
    assert "Job boom fallito" in caplog.text


@pytest.mark.django_db
def test_job_aste_e_giornate():
    assert jobs.auction_sweeper() == 0
    assert jobs.matchdays_maintenance() == {"worlds_leagues": 0, "backfilled": 0, "closed": 0, "waiting": 0}


@pytest.mark.django_db
def test_richiesta_di_sync_admin_eseguita_dallo_scheduler(admin_client):
    edition = lck_edition()
    response = admin_client.post("/api/admin/competitions/lck/synchronize")
    assert response.status_code == 202 and response.json()["requested"] is True
    assert ProviderSyncState.objects.filter(sync_requested_at__isnull=False).count() == 2
    with respx.mock(assert_all_called=False) as router:
        mock_lck(router)
        cargo_router(router, [])
        handled = jobs.manual_sync_requests()
    assert {h[0] for h in handled} == {"PANDASCORE", "LEAGUEPEDIA"}
    assert not ProviderSyncState.objects.filter(sync_requested_at__isnull=False).exists()
    assert edition.matches.count() == 3
    status = admin_client.get("/api/admin/competitions/LCK/synchronization").json()
    assert status["providers"][0]["provider"] == "PANDASCORE" and status["providers"][0]["status"] == "SUCCESS"


@pytest.mark.django_db
def test_comandi_di_gestione(capsys):
    lck_edition()
    with respx.mock(assert_all_called=False) as router:
        mock_lck(router)
        router.get("https://api.pandascore.test/leagues/293/series").respond(200, json=[])
        router.get("https://api.pandascore.test/lol/leagues").respond(200, json=[{"id": 297, "name":
                                                                                 "World Championship"}])
        cargo_router(router, [])
        call_command("sync_pandascore", competition="LCK", discover=True)
        assert json.loads(capsys.readouterr().out)["competitions"]["LCK"]["matches"] == 3
        call_command("enrich_leaguepedia", competition="LCK", limit=1)
        assert json.loads(capsys.readouterr().out)["skipped"] is False
        call_command("resolve_pandascore_leagues")
    assert Competition.objects.get(code="WORLDS").pandascore_league_id == 297
