"""Supporto ai test della pipeline: fixture JSON e mock HTTP (respx)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import respx

from apps.competitions.models import Competition, CompetitionEdition
from apps.providers.pandascore.worker import EsportsSyncWorker

FIXTURES = Path(__file__).parent / "fixtures"
PANDA = "https://api.pandascore.test"
LEAGUEPEDIA = "https://lol.leaguepedia.test"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def lck_edition() -> CompetitionEdition:
    return CompetitionEdition.objects.create(
        competition=Competition.objects.get(code="LCK"),
        year=2026,
        name="LCK 2026 Rounds 3-5",
        pandascore_serie_id=9001,
        pandascore_tournament_ids=[17001],
        starts_at=datetime(2026, 7, 20, tzinfo=UTC),
        ends_at=datetime(2026, 9, 10, tzinfo=UTC),
        is_active=True,
    )


def mock_lck(router: respx.MockRouter) -> None:
    router.get(f"{PANDA}/leagues/293/matches/past").mock(
        return_value=httpx.Response(200, json=load("pandascore/lck_past.json"), headers={"X-Total": "3"})
    )
    router.get(f"{PANDA}/leagues/293/matches/upcoming").mock(
        return_value=httpx.Response(200, json=load("pandascore/lck_upcoming.json"))
    )
    router.get(f"{PANDA}/leagues/293/matches/running").mock(return_value=httpx.Response(200, json=[]))
    router.get(f"{PANDA}/tournaments/17001/rosters").mock(
        return_value=httpx.Response(200, json=load("pandascore/lck_rosters.json"))
    )


def sync_lck() -> CompetitionEdition:
    edition = lck_edition()
    with respx.mock(assert_all_called=False) as router:
        mock_lck(router)
        EsportsSyncWorker().run("LCK")
    return edition


def cargo_router(router: respx.MockRouter, responses):
    """Login + sequenza di risposte cargoquery (lista di payload JSON)."""
    queue = list(responses)
    calls = []

    def handler(request: httpx.Request):
        params = dict(request.url.params)
        if request.method == "POST":
            return httpx.Response(200, json=load("leaguepedia/login_ok.json"))
        if params.get("meta") == "tokens":
            return httpx.Response(200, json=load("leaguepedia/login_token.json"))
        calls.append(params)
        payload = queue.pop(0) if queue else {"cargoquery": []}
        return httpx.Response(200, json=payload)

    router.route(host="lol.leaguepedia.test", path="/api.php").mock(side_effect=handler)
    return calls
