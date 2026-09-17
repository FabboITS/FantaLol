"""Client REST PandaScore (ex `pandascore_client.go` / `PandaScoreClient.java`).

Pattern lega x stato (`past`/`upcoming`/`running`), `per_page` massimo 100,
auth `Bearer`, timeout 20s. L'allowlist delle leghe arriva dalle settings:
nessun id di lega è hardcoded qui.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

MATCH_STATES = ("past", "running", "upcoming")


class PandaScoreError(RuntimeError):
    """Errore recuperabile: il chiamante prosegue con le altre leghe."""


@dataclass(frozen=True)
class ProLeagueConfig:
    """Una voce dell'allowlist `SUPPORTED_PRO_LEAGUES`."""

    code: str
    pandascore_id: int


def supported_leagues() -> list[ProLeagueConfig]:
    """Allowlist delle leghe pro da sincronizzare.

    Formato env: `LEC:4198,LPL:294,LCK:293,WORLDS:4198`. Le leghe Worlds si
    aggiungono qui (configurazione), non nel codice del client.
    """
    raw = settings.SUPPORTED_PRO_LEAGUES or ""
    leagues: list[ProLeagueConfig] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        code, _, league_id = chunk.partition(":")
        try:
            leagues.append(ProLeagueConfig(code=code.strip().upper(), pandascore_id=int(league_id)))
        except ValueError:
            logger.warning("Voce SUPPORTED_PRO_LEAGUES ignorata (id non numerico): %s", chunk)
    return leagues


class PandaScoreClient:
    def __init__(self, token: str | None = None, base_url: str | None = None,
                 timeout: float | None = None, client: httpx.Client | None = None):
        self.token = token if token is not None else settings.PANDASCORE["API_TOKEN"]
        self.base_url = (base_url or settings.PANDASCORE["API_BASE"]).rstrip("/")
        self.timeout = timeout or settings.PANDASCORE["TIMEOUT_SECONDS"]
        self.per_page = min(settings.PANDASCORE["PER_PAGE"], 100)
        self._client = client

    @property
    def configured(self) -> bool:
        """Senza token il sync non parte: si continua a servire la cache DB."""
        return bool(self.token)

    def _http(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
        )

    def _get(self, path: str, params: dict) -> list[dict]:
        client = self._http()
        close = self._client is None
        try:
            response = client.get(path, params=params)
            if response.status_code == 429:
                raise PandaScoreError("PandaScore rate limit raggiunto (429)")
            if response.status_code >= 400:
                raise PandaScoreError(
                    f"PandaScore ha risposto {response.status_code} su {path}")
            payload = response.json()
            return payload if isinstance(payload, list) else [payload]
        except httpx.HTTPError as exc:
            raise PandaScoreError(f"Errore di rete verso PandaScore: {exc}") from exc
        finally:
            if close:
                client.close()

    def matches_by_league_and_state(self, league_id: int, state: str) -> list[dict]:
        """Serie di una lega in un dato stato (`past`/`running`/`upcoming`)."""
        if state not in MATCH_STATES:
            raise ValueError(f"Stato non supportato: {state}")
        return self._get(
            f"/lol/matches/{state}",
            {
                "filter[league_id]": league_id,
                "sort": "begin_at",
                "per_page": self.per_page,
            },
        )

    def match(self, match_id: int) -> dict:
        result = self._get(f"/lol/matches/{match_id}", {})
        return result[0] if result else {}

    def tournament_matches(self, tournament_id: int) -> list[dict]:
        """Usata dalla modalità Worlds per importare le serie di una fase."""
        return self._get(
            "/lol/matches",
            {
                "filter[tournament_id]": tournament_id,
                "sort": "begin_at",
                "per_page": self.per_page,
            },
        )

    def tournament_teams(self, tournament_id: int) -> list[dict]:
        """Roster qualificati a un torneo (import player pool Worlds)."""
        return self._get(f"/lol/tournaments/{tournament_id}/teams", {"per_page": self.per_page})
