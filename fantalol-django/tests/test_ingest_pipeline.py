"""Porting di `OracleGameImportServiceTest` / `LecSynchronizationServiceTest`,
riadattati alla pipeline PandaScore + Leaguepedia. Nessuna chiamata HTTP reale.
"""
from datetime import timedelta

import httpx
import pytest
from django.utils import timezone

from ingest import services
from ingest.leaguepedia_client import LeaguepediaClient, LeaguepediaError
from ingest.models import (
    Game,
    GamePlayerStat,
    Match,
    MatchStatus,
    PlayerAlias,
    SyncState,
    SyncStatus,
    TeamAlias,
)
from ingest.pandascore_client import PandaScoreClient, supported_leagues
from teams.models import PlayerRole

from .factories import MatchFactory, ProPlayerFactory, ProTeamFactory

pytestmark = pytest.mark.django_db


def pandascore_payload(match_id: int, status: str = "finished") -> dict:
    return {
        "id": match_id,
        "slug": f"serie-{match_id}",
        "name": f"Serie {match_id}",
        "status": status,
        "begin_at": "2026-09-10T16:00:00Z",
        "end_at": "2026-09-10T18:00:00Z",
        "number_of_games": 3,
        "league": {"id": 4198, "name": "LEC"},
        "tournament": {"name": "Season Finals"},
        "serie": {"full_name": "Summer 2026"},
        "opponents": [{"opponent": {"name": "G2 Esports"}}, {"opponent": {"name": "Fnatic"}}],
        "results": [{"score": 2}, {"score": 1}],
        "winner": {"name": "G2 Esports"},
    }


# --- allowlist ------------------------------------------------------------
def test_supported_leagues_are_configuration_not_code(settings):
    settings.SUPPORTED_PRO_LEAGUES = "LEC:4198,LPL:294,WORLDS:4321"
    codes = [league.code for league in supported_leagues()]
    assert codes == ["LEC", "LPL", "WORLDS"]


def test_malformed_allowlist_entries_are_ignored(settings):
    settings.SUPPORTED_PRO_LEAGUES = "LEC:4198,BROKEN,LCK:non-numerico"
    assert [l.code for l in supported_leagues()] == ["LEC"]


# --- upsert idempotente ---------------------------------------------------
def test_upsert_is_idempotent():
    payload = pandascore_payload(777)
    match, created = services.upsert_match(payload, "LEC")
    assert created is True
    same, created_again = services.upsert_match(payload, "LEC")
    assert created_again is False
    assert same.pk == match.pk
    assert Match.objects.count() == 1


def test_upsert_updates_status_and_results():
    services.upsert_match(pandascore_payload(778, status="running"), "LEC")
    match, _ = services.upsert_match(pandascore_payload(778, status="finished"), "LEC")
    assert match.status == MatchStatus.FINISHED
    assert match.winner_name == "G2 Esports"
    assert match.opponents == ["G2 Esports", "Fnatic"]


# --- fallimento parziale --------------------------------------------------
def test_sync_without_token_is_skipped_and_serves_cache(settings):
    settings.PANDASCORE = {**settings.PANDASCORE, "API_TOKEN": ""}
    report = services.sync_pandascore(PandaScoreClient(token=""))
    assert report.skipped == 1
    state = SyncState.objects.get(provider=services.PANDASCORE_PROVIDER)
    assert "PANDASCORE_API_TOKEN assente" in state.last_error


def test_a_failing_league_does_not_abort_the_cycle(settings):
    settings.SUPPORTED_PRO_LEAGUES = "LEC:4198,LPL:294"

    def handler(request: httpx.Request) -> httpx.Response:
        if "294" in str(request.url):
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json=[pandascore_payload(900)])

    client = PandaScoreClient(token="t", client=httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.test"))
    report = services.sync_pandascore(client)

    # LEC upserta la stessa serie per i tre stati, LPL fallisce tre volte.
    assert report.inserted + report.updated == 3
    assert report.failed == 3
    state = SyncState.objects.get(provider=services.PANDASCORE_PROVIDER)
    assert state.status == SyncStatus.PARTIAL
    assert "LPL" in state.last_error


# --- alias ----------------------------------------------------------------
def test_player_alias_resolves_name_mismatches():
    player = ProPlayerFactory(nickname="Caps")
    PlayerAlias.objects.create(source_name="Caps (LEC)", canonical_name="Caps", player=player)
    assert services.resolve_player("Caps (LEC)") == player
    assert services.resolve_player("Caps") == player
    assert services.resolve_player("Sconosciuto") is None


def test_team_alias_maps_pandascore_names_to_leaguepedia():
    team = ProTeamFactory(nome="Movistar KOI", leaguepedia_name="Movistar KOI")
    TeamAlias.objects.create(source_name="MKOI", canonical_name="Movistar KOI", team=team)
    assert services.canonical_team_name("MKOI") == "Movistar KOI"
    assert services.resolve_team("MKOI") == team


# --- enrich ---------------------------------------------------------------
class FakeLeaguepediaClient:
    """Doppio di test: nessuna richiesta HTTP, nessun throttling."""

    configured = True

    def __init__(self, games, players, error: Exception | None = None):
        self.games = games
        self.players = players
        self.error = error
        self.calls = 0

    def games_for_window(self, teams, begin_at, end_at):
        self.calls += 1
        if self.error:
            raise self.error
        return self.games

    def player_stats_for_games(self, game_ids):
        return [row for row in self.players if row["GameId"] in game_ids]


def box_score(game_id: str, link: str, role: str, **overrides) -> dict:
    row = {
        "GameId": game_id, "Link": link, "Name": link, "Team": "G2 Esports", "Role": role,
        "Champion": "Ahri", "Kills": "3", "Deaths": "1", "Assists": "5", "CS": "250",
        "Gold": "12000", "DamageToChampions": "18000", "VisionScore": "40", "PlayerWin": "Yes",
    }
    row.update(overrides)
    return row


def test_enrich_creates_games_and_computes_fantasy_scores():
    match = MatchFactory(opponents=["G2 Esports", "Fnatic"])
    player = ProPlayerFactory(nickname="Caps", ruolo=PlayerRole.MID)
    client = FakeLeaguepediaClient(
        games=[{"GameId": "LEC/2026 Season/G1", "DateTime_UTC": "2026-09-10 16:30:00",
                "Team1": "G2 Esports", "Team2": "Fnatic", "WinTeam": "G2 Esports",
                "Gamelength_Number": "31.5", "Patch": "16.18", "MVP": "Caps",
                "N_GameInMatch": "1"}],
        players=[box_score("LEC/2026 Season/G1", "Caps", "Mid")],
    )
    report = services.enrich_match(match, client)
    match.refresh_from_db()

    assert report.failed == 0
    assert match.leaguepedia_synced_at is not None
    game = Game.objects.get(external_game_id="LEC/2026 Season/G1")
    assert game.mvp_player_id == player.id
    stat = GamePlayerStat.objects.get(game=game, player=player)
    # MID: 3*3 + 5*2 - 1*2 + (250/100)*1.00 + 3 = 22.5
    assert stat.fantasy_score == pytest.approx(22.5)


def test_enrich_is_idempotent_and_never_duplicates_games():
    match = MatchFactory(opponents=["G2 Esports", "Fnatic"])
    ProPlayerFactory(nickname="Caps", ruolo=PlayerRole.MID)
    rows = [{"GameId": "G1", "DateTime_UTC": "2026-09-10 16:30:00", "Team1": "G2 Esports",
             "Team2": "Fnatic", "WinTeam": "G2 Esports", "N_GameInMatch": "1"}]
    stats = [box_score("G1", "Caps", "Mid")]

    services.enrich_match(match, FakeLeaguepediaClient(rows, stats))
    services.enrich_match(match, FakeLeaguepediaClient(rows, stats))
    assert Game.objects.filter(external_game_id="G1").count() == 1
    assert GamePlayerStat.objects.count() == 1


def test_enrich_failure_is_recorded_without_marking_the_series_synced():
    match = MatchFactory(opponents=["G2 Esports", "Fnatic"])
    client = FakeLeaguepediaClient([], [], error=LeaguepediaError("429 rate limit"))
    report = services.enrich_match(match, client)
    match.refresh_from_db()
    assert report.failed == 1
    assert match.leaguepedia_synced_at is None
    assert match.leaguepedia_checked_at is not None
    assert match.leaguepedia_attempts == 1
    assert "rate limit" in match.leaguepedia_error


def test_unmapped_players_are_reported_not_fatal():
    match = MatchFactory(opponents=["G2 Esports", "Fnatic"])
    client = FakeLeaguepediaClient(
        games=[{"GameId": "G9", "DateTime_UTC": "2026-09-10 16:30:00", "Team1": "G2 Esports",
                "Team2": "Fnatic", "WinTeam": "G2 Esports", "N_GameInMatch": "1"}],
        players=[box_score("G9", "PlayerSconosciuto", "Mid")],
    )
    services.enrich_match(match, client)
    match.refresh_from_db()
    assert match.leaguepedia_synced_at is not None
    assert "PlayerSconosciuto" in match.leaguepedia_error
    assert GamePlayerStat.objects.count() == 0


# --- coda di enrich -------------------------------------------------------
def test_enrich_queue_takes_finished_unsynced_series_oldest_first():
    now = timezone.now()
    recent = MatchFactory(end_at=now - timedelta(hours=1), leaguepedia_checked_at=now)
    stale = MatchFactory(end_at=now - timedelta(days=2), leaguepedia_checked_at=None)
    MatchFactory(status=MatchStatus.NOT_STARTED, end_at=now - timedelta(hours=2))
    MatchFactory(end_at=now - timedelta(hours=3), leaguepedia_synced_at=now)

    queue = list(services.matches_to_enrich(10, now=now))
    assert queue == [stale, recent]


def test_series_older_than_the_give_up_window_are_abandoned(settings):
    settings.LEAGUEPEDIA = {**settings.LEAGUEPEDIA, "GIVE_UP_AFTER_DAYS": 7}
    now = timezone.now()
    MatchFactory(end_at=now - timedelta(days=9))
    assert list(services.matches_to_enrich(10, now=now)) == []


def test_enrich_batch_is_limited(settings):
    now = timezone.now()
    for _ in range(5):
        MatchFactory(end_at=now - timedelta(hours=2))
    assert len(list(services.matches_to_enrich(3, now=now))) == 3


# --- client Leaguepedia ---------------------------------------------------
def test_leaguepedia_client_throttles_between_requests():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(timezone.now())
        return httpx.Response(200, json={"cargoquery": [{"title": {"GameId": "G1"}}]})

    client = LeaguepediaClient(min_interval=0.05, client=httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://lol.test"))
    client.cargo_query(tables="ScoreboardGames")
    client.cargo_query(tables="ScoreboardGames")
    assert len(calls) == 2
    assert (calls[1] - calls[0]).total_seconds() >= 0.04


def test_leaguepedia_rate_limit_raises_a_recoverable_error():
    client = LeaguepediaClient(min_interval=0, client=httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(429)),
        base_url="https://lol.test"))
    with pytest.raises(LeaguepediaError, match="429"):
        client.cargo_query(tables="ScoreboardGames")


def test_leaguepedia_client_requires_two_teams():
    client = LeaguepediaClient(min_interval=0)
    with pytest.raises(LeaguepediaError, match="due squadre"):
        client.games_for_window(["Solo una"], timezone.now(), timezone.now())
