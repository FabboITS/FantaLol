"""Client PandaScore (piano gratuito "Fixtures": solo endpoint di lista).

Il dettaglio singolo ``GET /lol/matches/{id}`` e le statistiche post-game richiedono il piano Historical:
qui si usano soltanto ``/leagues/{id}/matches/{past|upcoming|running}``, ``/leagues/{id}/series``,
``/tournaments/{id}/rosters`` e ``/leagues?search[name]=``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

MATCH_STATES = ("past", "upcoming", "running")


class PandaScoreError(Exception):
    pass


class PandaScoreNotConfigured(PandaScoreError):
    pass


def _retryable(error: BaseException) -> bool:
    if isinstance(error, httpx.TransportError):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 429 or error.response.status_code >= 500
    return False


@dataclass
class Page:
    items: list[dict]
    total: int | None
    has_next: bool


class PandaScoreClient:
    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.token = token if token is not None else settings.PANDASCORE_API_TOKEN
        if not self.token:
            raise PandaScoreNotConfigured("PANDASCORE_API_TOKEN non configurato")
        self.client = httpx.Client(
            base_url=(base_url or settings.PANDASCORE_API_BASE).rstrip("/"),
            timeout=timeout or settings.HTTP_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @retry(
        retry=retry_if_exception(_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response

    @staticmethod
    def validate_per_page(per_page: int) -> int:
        if not isinstance(per_page, int) or not 1 <= per_page <= 100:
            raise ValueError("per_page deve essere compreso tra 1 e 100")
        return per_page

    def _page(self, path: str, params: dict) -> Page:
        response = self._get(path, params)
        data = response.json()
        total = response.headers.get("X-Total")
        has_next = 'rel="next"' in response.headers.get("Link", "")
        if total is not None and not has_next:
            page, per_page = int(params.get("page", 1)), int(params.get("per_page", 50))
            has_next = page * per_page < int(total)
        return Page(
            items=data if isinstance(data, list) else [],
            total=int(total) if total else None,
            has_next=has_next,
        )

    def league_matches(self, league_id: int, state: str, *, page: int = 1, per_page: int = 100) -> Page:
        if state not in MATCH_STATES:
            raise ValueError(f"Stato non valido: {state}")
        params: dict = {"page": page, "per_page": self.validate_per_page(per_page)}
        if state == "past":
            params["sort"] = "-begin_at"
            params["filter[status]"] = "finished"
        else:
            params["sort"] = "begin_at"
        return self._page(f"/leagues/{league_id}/matches/{state}", params)

    def league_series(self, league_id: int, *, per_page: int = 20) -> list[dict]:
        params = {"sort": "-begin_at", "per_page": self.validate_per_page(per_page)}
        return self._page(f"/leagues/{league_id}/series", params).items

    def tournament_rosters(self, tournament_id: int) -> list[dict]:
        data = self._get(f"/tournaments/{tournament_id}/rosters").json()
        if isinstance(data, dict):
            return data.get("rosters", [])
        return data if isinstance(data, list) else []

    def search_leagues(self, name: str) -> list[dict]:
        return self._page("/lol/leagues", {"search[name]": name, "per_page": 50}).items

    def download(self, url: str, etag: str | None = None) -> httpx.Response:
        headers = {"If-None-Match": etag} if etag else {}
        with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS, follow_redirects=True) as raw:
            return raw.get(url, headers=headers)
