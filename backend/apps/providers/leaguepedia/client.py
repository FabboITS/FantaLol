"""Client Cargo di Leaguepedia (``lol.fandom.com/api.php``).

* login con bot password (``Utente@NomeBot``) via ``action=login`` con token, sessione persistente;
* self-throttle (~1 richiesta/secondo) protetto da lock;
* errore ``ratelimited`` → ``LeaguepediaRateLimited`` che interrompe l'intero ciclo di arricchimento;
* tutti i valori interpolati nelle clausole ``where`` passano da ``escape_cargo_string``.

I contenuti Leaguepedia sono rilasciati con licenza CC BY-SA: l'attribuzione è restituita dalle API.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterable
from datetime import UTC, datetime

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

PLAYER_ROW_LIMIT = 500


class LeaguepediaError(Exception):
    pass


class LeaguepediaRateLimited(LeaguepediaError):
    pass


class LeaguepediaNotConfigured(LeaguepediaError):
    pass


def escape_cargo_string(value: str) -> str:
    """Escape di backslash e apici per i letterali stringa nelle query Cargo."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")


def cargo_datetime(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _field(row: dict, *names: str):
    """Cargo può restituire le chiavi con spazi al posto degli underscore: si accettano entrambe."""
    for name in names:
        for key in (name, name.replace("_", " ")):
            if key in row and row[key] not in ("", None):
                return row[key]
    return None


class LeaguepediaClient:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        base_url: str | None = None,
        min_interval: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.username = username if username is not None else settings.LEAGUEPEDIA_BOT_USERNAME
        self.password = password if password is not None else settings.LEAGUEPEDIA_BOT_PASSWORD
        if not self.username or not self.password:
            raise LeaguepediaNotConfigured(
                "LEAGUEPEDIA_BOT_USERNAME / LEAGUEPEDIA_BOT_PASSWORD non configurate"
            )
        self.base_url = (base_url or settings.LEAGUEPEDIA_API_BASE).rstrip("/")
        self.min_interval = (
            settings.LEAGUEPEDIA_MIN_INTERVAL_SECONDS if min_interval is None else min_interval
        )
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            transport=transport,
            headers={"User-Agent": "FantaLol/2.0 (fantasy LoL)"},
        )
        self._lock = threading.Lock()
        self._last_request = 0.0
        self._logged_in = False

    def close(self) -> None:
        self.client.close()

    # ----------------------------------------------------------------- trasporto
    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _call(self, method: str, params: dict) -> dict:
        with self._lock:
            self._throttle()
            params = {**params, "format": "json"}
            if method == "POST":
                response = self.client.post("/api.php", data=params)
            else:
                response = self.client.get("/api.php", params=params)
        if response.status_code == 429:
            raise LeaguepediaRateLimited("HTTP 429 da Leaguepedia")
        response.raise_for_status()
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if error:
            if error.get("code") == "ratelimited":
                raise LeaguepediaRateLimited(error.get("info") or "ratelimited")
            raise LeaguepediaError(f"{error.get('code')}: {error.get('info')}")
        return payload

    def login(self) -> None:
        if self._logged_in:
            return
        token = self._call("GET", {"action": "query", "meta": "tokens", "type": "login"})
        login_token = token["query"]["tokens"]["logintoken"]
        result = self._call(
            "POST",
            {"action": "login", "lgname": self.username, "lgpassword": self.password, "lgtoken": login_token},
        )
        if (result.get("login") or {}).get("result") != "Success":
            raise LeaguepediaError(f"Login Leaguepedia fallito: {(result.get('login') or {}).get('reason')}")
        self._logged_in = True

    def cargo(
        self,
        *,
        tables: str,
        fields: str,
        where: str,
        join_on: str | None = None,
        limit: int = 500,
        order_by: str | None = None,
    ) -> list[dict]:
        self.login()
        params = {"action": "cargoquery", "tables": tables, "fields": fields, "where": where, "limit": limit}
        if join_on:
            params["join_on"] = join_on
        if order_by:
            params["order_by"] = order_by
        payload = self._call("GET", params)
        return [row.get("title", {}) for row in payload.get("cargoquery", [])]

    # ----------------------------------------------------------------- query di dominio
    def list_games(self, team1: str, team2: str, date_from: datetime, date_to: datetime) -> list[dict]:
        a, b = escape_cargo_string(team1), escape_cargo_string(team2)
        where = (
            f'((SG.Team1="{a}" AND SG.Team2="{b}") OR (SG.Team1="{b}" AND SG.Team2="{a}"))'
            f' AND SG.DateTime_UTC >= "{cargo_datetime(date_from)}"'
            f' AND SG.DateTime_UTC <= "{cargo_datetime(date_to)}"'
        )
        rows = self.cargo(
            tables="ScoreboardGames=SG,MatchScheduleGame=MSG",
            join_on="SG.GameId=MSG.GameId",
            fields=(
                "SG.GameId=GameId,SG.Team1=Team1,SG.Team2=Team2,SG.WinTeam=WinTeam,"
                "SG.Gamelength_Number=GameLengthMinutes,SG.DateTime_UTC=DateTimeUTC,"
                "SG.N_GameInMatch=GameInMatch,SG.OverviewPage=OverviewPage,MSG.MVP=MVP"
            ),
            where=where,
            order_by="SG.DateTime_UTC ASC",
        )
        return [
            {
                "game_id": _field(row, "GameId"),
                "team1": _field(row, "Team1"),
                "team2": _field(row, "Team2"),
                "win_team": _field(row, "WinTeam"),
                "length_minutes": _field(row, "GameLengthMinutes"),
                "datetime_utc": _field(row, "DateTimeUTC", "DateTime_UTC"),
                "game_in_match": _field(row, "GameInMatch", "N_GameInMatch"),
                "overview_page": _field(row, "OverviewPage"),
                "mvp": _field(row, "MVP"),
            }
            for row in rows
            if _field(row, "GameId")
        ]

    def list_player_stats(self, game_ids: Iterable[str]) -> list[dict]:
        """Una sola query per serie: ``SP.GameId IN (...)`` invece di una chiamata per game."""
        ids = [g for g in game_ids if g]
        if not ids:
            return []
        in_list = ",".join(f'"{escape_cargo_string(g)}"' for g in ids)
        rows = self.cargo(
            tables="ScoreboardPlayers=SP",
            fields=(
                "SP.Link=Link,SP.Champion=Champion,SP.Kills=Kills,SP.Deaths=Deaths,SP.Assists=Assists,"
                "SP.Gold=Gold,SP.CS=CS,SP.DamageToChampions=DamageToChampions,SP.VisionScore=VisionScore,"
                "SP.Role=Role,SP.Side=Side,SP.PlayerWin=PlayerWin,SP.GameId=GameId,SP.Team=Team,"
                "SP.OverviewPage=OverviewPage"
            ),
            where=f"SP.GameId IN ({in_list})",
            limit=PLAYER_ROW_LIMIT,
        )
        return [
            {
                "link": _field(row, "Link"),
                "champion": _field(row, "Champion"),
                "kills": _field(row, "Kills"),
                "deaths": _field(row, "Deaths"),
                "assists": _field(row, "Assists"),
                "gold": _field(row, "Gold"),
                "cs": _field(row, "CS"),
                "damage_to_champions": _field(row, "DamageToChampions"),
                "vision_score": _field(row, "VisionScore"),
                "role": _field(row, "Role"),
                "side": _field(row, "Side"),
                "player_win": _field(row, "PlayerWin"),
                "game_id": _field(row, "GameId"),
                "team": _field(row, "Team"),
                "overview_page": _field(row, "OverviewPage"),
            }
            for row in rows
        ]
