"""Client Cargo API di Leaguepedia (ex `leaguepedia_client.go`).

Due query per serie:
 1. `ScoreboardGames` LEFT JOIN `MatchScheduleGame` per elencare i game della
    serie e recuperarne il `GameId`;
 2. `ScoreboardPlayers` per i 10 box score di ogni game.

Self-throttling a ~1 req/sec e gestione esplicita del rate limit.
I dati restituiti sono coperti da licenza CC BY-SA 3.0 (cfr. `ATTRIBUTION`).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class LeaguepediaError(RuntimeError):
    """Errore recuperabile: la serie viene ritentata al ciclo successivo."""


class LeaguepediaRateLimited(LeaguepediaError):
    pass


class LeaguepediaClient:
    #: Campi richiesti a `ScoreboardPlayers`: sono esattamente quelli che la
    #: formula fantapunti usa (KDA, CS, gold, damage, vision score, Link).
    PLAYER_FIELDS = (
        "SP.GameId, SP.Link, SP.Name, SP.Team, SP.Role, SP.Champion, SP.Kills, SP.Deaths, "
        "SP.Assists, SP.CS, SP.Gold, SP.DamageToChampions, SP.VisionScore, SP.PlayerWin"
    )
    GAME_FIELDS = (
        "SG.GameId, SG.DateTime_UTC, SG.Team1, SG.Team2, SG.WinTeam, SG.Gamelength_Number, "
        "SG.Patch, SG.MVP, SG.OverviewPage, MSG.N_GameInMatch"
    )

    def __init__(self, base_url: str | None = None, timeout: float | None = None,
                 min_interval: float | None = None, client: httpx.Client | None = None):
        self.base_url = (base_url or settings.LEAGUEPEDIA["API_BASE"]).rstrip("/")
        self.timeout = timeout or settings.LEAGUEPEDIA["TIMEOUT_SECONDS"]
        self.min_interval = (min_interval if min_interval is not None
                             else settings.LEAGUEPEDIA["MIN_REQUEST_INTERVAL_SECONDS"])
        self._client = client
        self._lock = threading.Lock()
        self._last_request_at = 0.0

    @property
    def configured(self) -> bool:
        """Senza credenziali bot si servono solo i game già arricchiti."""
        return bool(settings.LEAGUEPEDIA["BOT_USERNAME"] and settings.LEAGUEPEDIA["BOT_PASSWORD"])

    def _throttle(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_at = time.monotonic()

    def _http(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": "FantaLoL/2.0 (ingest; contact: admin@fantalol.local)"},
        )

    def cargo_query(self, **params) -> list[dict]:
        self._throttle()
        client = self._http()
        close = self._client is None
        query = {"action": "cargoquery", "format": "json", "limit": "500"}
        query.update(params)
        try:
            response = client.get("/api.php", params=query)
            if response.status_code == 429:
                raise LeaguepediaRateLimited("Leaguepedia rate limit raggiunto (429)")
            if response.status_code >= 400:
                raise LeaguepediaError(f"Leaguepedia ha risposto {response.status_code}")
            payload = response.json()
        except httpx.HTTPError as exc:
            raise LeaguepediaError(f"Errore di rete verso Leaguepedia: {exc}") from exc
        finally:
            if close:
                client.close()

        if "error" in payload:
            raise LeaguepediaError(str(payload["error"].get("info", payload["error"])))
        return [row.get("title", {}) for row in payload.get("cargoquery", [])]

    def games_for_window(self, teams: list[str], begin_at: datetime, end_at: datetime) -> list[dict]:
        """Game disputati fra due squadre nella finestra temporale indicata.

        La finestra è volutamente larga (`begin_at - 6h` .. `end_at + 12h`,
        applicata dal chiamante) perché gli orari Leaguepedia non coincidono
        con quelli PandaScore.
        """
        if len(teams) != 2:
            raise LeaguepediaError("Servono esattamente due squadre per risolvere una serie")
        team1, team2 = (self._escape(team) for team in teams)
        where = (
            f"SG.DateTime_UTC >= '{begin_at:%Y-%m-%d %H:%M:%S}' "
            f"AND SG.DateTime_UTC <= '{end_at:%Y-%m-%d %H:%M:%S}' "
            f"AND ((SG.Team1 = '{team1}' AND SG.Team2 = '{team2}') "
            f"OR (SG.Team1 = '{team2}' AND SG.Team2 = '{team1}'))"
        )
        return self.cargo_query(
            tables="ScoreboardGames=SG,MatchScheduleGame=MSG",
            join_on="SG.GameId=MSG.GameId",
            fields=self.GAME_FIELDS,
            where=where,
            order_by="SG.DateTime_UTC ASC",
        )

    def player_stats_for_games(self, game_ids: list[str]) -> list[dict]:
        """I 10 box score di ciascun game richiesto."""
        if not game_ids:
            return []
        clause = " OR ".join(f"SP.GameId = '{self._escape(gid)}'" for gid in game_ids)
        return self.cargo_query(
            tables="ScoreboardPlayers=SP",
            fields=self.PLAYER_FIELDS,
            where=clause,
            order_by="SP.GameId ASC",
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("'", "\\'")
