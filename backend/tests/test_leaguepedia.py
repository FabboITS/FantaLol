"""Leaguepedia: escape Cargo, login, arricchimento, alias, MISSING, give-up, rate limit, endpoint 5.3."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from freezegun import freeze_time

from apps.competitions.models import Competition, CompetitionEdition
from apps.esports.models import (
    EditionRoster,
    EsportsGame,
    EsportsMatch,
    GamePlayerStat,
    PlayerAlias,
    ProPlayer,
    ProTeam,
    ProviderSyncState,
    TeamAlias,
)
from apps.providers.leaguepedia.client import (
    LeaguepediaClient,
    LeaguepediaError,
    LeaguepediaNotConfigured,
    LeaguepediaRateLimited,
    escape_cargo_string,
)
from apps.providers.leaguepedia.worker import LeaguepediaEnrichWorker
from apps.providers.sync_state import record_success

from .factories import EditionFactory, TeamFactory, add_match
from .pipeline_helpers import cargo_router, load, sync_lck

pytestmark = pytest.mark.django_db
NOW = "2026-08-02T12:00:00Z"


def test_escape_cargo_string():
    assert escape_cargo_string("Gen.G") == "Gen.G"
    assert escape_cargo_string('Team "Q"') == 'Team \\"Q\\"'
    assert escape_cargo_string("Rogue's") == "Rogue\\'s"
    assert escape_cargo_string("a\\b") == "a\\\\b"
    assert escape_cargo_string('x" OR 1=1 --') == 'x\\" OR 1=1 --'


def test_credenziali_bot_obbligatorie(settings):
    settings.LEAGUEPEDIA_BOT_PASSWORD = None
    with pytest.raises(LeaguepediaNotConfigured):
        LeaguepediaClient()
    assert LeaguepediaEnrichWorker().run() == {"skipped": True}


@respx.mock
def test_login_con_token_e_query_cargo():
    calls = cargo_router(respx.mock, [load("leaguepedia/lck_games.json")])
    client = LeaguepediaClient()
    games = client.list_games(
        'Gen."G', "T1", datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 8, 2, tzinfo=UTC)
    )
    assert len(games) == 3 and games[0]["game_in_match"] == "1" and games[0]["mvp"] == "Chovy"
    assert calls[0]["tables"] == "ScoreboardGames=SG,MatchScheduleGame=MSG"
    assert calls[0]["join_on"] == "SG.GameId=MSG.GameId"
    assert 'SG.Team1="Gen.\\"G"' in calls[0]["where"]
    assert 'SG.DateTime_UTC >= "2026-08-01 00:00:00"' in calls[0]["where"]
    login_post = [c for c in respx.mock.calls if c.request.method == "POST"][0].request
    assert b"lgname=Tester%40FantaLol" in login_post.content


@respx.mock
def test_una_sola_query_per_serie_con_gameid_in():
    calls = cargo_router(respx.mock, [load("leaguepedia/lck_players.json")])
    rows = LeaguepediaClient().list_player_stats(["G1", "G'2"])
    assert len(rows) == 30
    assert calls[0]["where"] == 'SP.GameId IN ("G1","G\\\'2")'
    assert LeaguepediaClient().list_player_stats([]) == []


@respx.mock
def test_errore_ratelimited_e_errori_api():
    respx.route(host="lol.leaguepedia.test").mock(
        return_value=httpx.Response(200, json=load("leaguepedia/ratelimited.json"))
    )
    with pytest.raises(LeaguepediaRateLimited):
        LeaguepediaClient().login()
    respx.route(host="lol.leaguepedia.test").mock(
        return_value=httpx.Response(200, json={"error": {"code": "badtoken", "info": "Invalid token"}})
    )
    with pytest.raises(LeaguepediaError):
        LeaguepediaClient().login()


def _lck_ready():
    edition = sync_lck()
    record_success("PANDASCORE", edition.competition)
    return edition, EsportsMatch.objects.get(pandascore_id=1100001)


@freeze_time(NOW)
def test_arricchimento_serie_lck_completa():
    edition, match = _lck_ready()
    with respx.mock(assert_all_called=False) as router:
        calls = cargo_router(
            router, [load("leaguepedia/lck_games.json"), load("leaguepedia/lck_players.json")]
        )
        report = LeaguepediaEnrichWorker().run(limit=1)
    assert report["processed"] == 1 and not report["errors"]
    match.refresh_from_db()
    assert match.leaguepedia_synced_at and match.stats_complete
    games = list(match.games.order_by("game_number"))
    assert [g.game_number for g in games] == [1, 2, 3]
    assert games[0].winner_team.name == "Gen.G" and games[1].winner_team.name == "T1"
    assert games[0].mvp_link == "Chovy" and games[0].length_seconds == 1890
    assert GamePlayerStat.objects.filter(game__match=match).count() == 30
    chovy = ProPlayer.objects.get(nickname="Chovy")
    assert chovy.leaguepedia_link == "Chovy (Jeong Ji-hoon)"  # risolto per nickname + team dell'edizione
    stat = GamePlayerStat.objects.get(game=games[0], player=chovy)
    assert stat.role == "MID" and stat.side == "Blue" and stat.win is True and stat.is_complete
    # Finestra di ricerca: begin_at - 6h … end_at + 12h.
    assert '"2026-08-01 02:00:00"' in calls[0]["where"] and '"2026-08-01 22:40:00"' in calls[0]["where"]
    state = ProviderSyncState.objects.get(provider="LEAGUEPEDIA", competition=edition.competition)
    assert state.status == "SUCCESS" and state.inserted_games == 3


@freeze_time(NOW)
def test_alias_team_nella_query_e_alias_player():
    edition = EditionFactory(competition=Competition.objects.get(code="LCK"))
    ns = TeamFactory(name="Nongshim Red Force")
    hle = TeamFactory(name="Hanwha Life Esports")
    TeamAlias.objects.create(pandascore_name="Nongshim Red Force", leaguepedia_name="Nongshim RedForce")
    player = ProPlayer.objects.create(nickname="Scout")
    PlayerAlias.objects.create(player=player, leaguepedia_link="Scout (Lee Ye-chan)")
    match = add_match(
        edition,
        ns,
        hle,
        begin=datetime(2026, 8, 1, 8, tzinfo=UTC),
        winner=hle,
        score=(0, 1),
        stats_complete=False,
    )
    games = {
        "cargoquery": [
            {
                "title": {
                    "GameId": "G1",
                    "Team1": "Nongshim RedForce",
                    "Team2": "Hanwha Life Esports",
                    "WinTeam": "Hanwha Life Esports",
                    "GameInMatch": "1",
                    "DateTimeUTC": "2026-08-01 08:05:00",
                }
            }
        ]
    }
    players = {
        "cargoquery": [
            {
                "title": {
                    "Link": "Scout (Lee Ye-chan)",
                    "GameId": "G1",
                    "Team": "Nongshim RedForce",
                    "Role": "Mid",
                    "Kills": "1",
                    "Deaths": "2",
                    "Assists": "3",
                    "CS": "250",
                    "VisionScore": "20",
                    "PlayerWin": "No",
                    "Champion": "Azir",
                }
            }
        ]
    }
    with respx.mock(assert_all_called=False) as router:
        calls = cargo_router(router, [games, players])
        LeaguepediaEnrichWorker().run(limit=1)
    assert 'SG.Team1="Nongshim RedForce"' in calls[0]["where"]
    stat = GamePlayerStat.objects.get(leaguepedia_link="Scout (Lee Ye-chan)")
    assert stat.player == player and stat.team == ns
    assert EsportsGame.objects.get(match=match).winner_team == hle


@freeze_time(NOW)
def test_lpl_righe_missing_e_player_non_associati_restano_provvisori():
    edition = EditionFactory(competition=Competition.objects.get(code="LPL"))
    blg, tes = TeamFactory(name="Bilibili Gaming"), TeamFactory(name="Top Esports")
    for nick, team, role in (("Bin", blg, "TOP"), ("Elk", blg, "ADC"), ("Kanavi", tes, "JUNGLE")):
        EditionRoster.objects.create(
            edition=edition,
            team=team,
            player=ProPlayer.objects.create(nickname=nick),
            role=role,
            active_from=edition.starts_at,
        )
    match = add_match(
        edition,
        blg,
        tes,
        begin=datetime(2026, 8, 2, 9, tzinfo=UTC),
        winner=tes,
        score=(0, 1),
        stats_complete=False,
    )
    with respx.mock(assert_all_called=False) as router:
        cargo_router(router, [load("leaguepedia/lpl_games.json"), load("leaguepedia/lpl_players.json")])
        report = LeaguepediaEnrichWorker().run()
    match.refresh_from_db()
    assert match.leaguepedia_synced_at is None and match.leaguepedia_checked_at is not None
    assert not match.stats_complete
    missing = GamePlayerStat.objects.get(leaguepedia_link__startswith="MISSING")
    assert missing.player is None and not missing.is_complete
    bin_row = GamePlayerStat.objects.get(leaguepedia_link="Bin")
    assert bin_row.kills is None and not bin_row.is_complete
    assert "NuovoTalento" in report["unmatched"]
    state = ProviderSyncState.objects.get(provider="LEAGUEPEDIA", competition=edition.competition)
    assert "NuovoTalento" in state.unmatched_players


def test_zero_game_rimette_in_coda_e_give_up_dopo_sette_giorni():
    edition = EditionFactory(competition=Competition.objects.get(code="LPL"))
    match = add_match(
        edition,
        TeamFactory(),
        TeamFactory(),
        begin=datetime(2026, 8, 1, 9, tzinfo=UTC),
        winner=None,
        stats_complete=False,
    )
    other = add_match(
        edition,
        TeamFactory(),
        TeamFactory(),
        begin=datetime(2026, 8, 1, 12, tzinfo=UTC),
        winner=None,
        stats_complete=False,
    )
    with freeze_time("2026-08-02T00:00:00Z"), respx.mock(assert_all_called=False) as router:
        cargo_router(router, [])
        LeaguepediaEnrichWorker().run(limit=1)
    # Ordine dell'indice parziale: mai controllati prima, poi end_at più recente.
    other.refresh_from_db()
    assert other.leaguepedia_checked_at is not None and other.leaguepedia_synced_at is None
    # Il match controllato torna in fondo alla coda: ora tocca all'altro (mai controllato).
    assert list(LeaguepediaEnrichWorker.queue()) == [match, other]
    with freeze_time("2026-08-09T00:00:00Z"), respx.mock(assert_all_called=False) as router:
        cargo_router(router, [])
        LeaguepediaEnrichWorker().run()
    match.refresh_from_db()
    assert match.leaguepedia_synced_at is not None and not match.stats_complete


def test_match_senza_due_team_marcato_come_sincronizzato():
    edition = EditionFactory()
    match = EsportsMatch.objects.create(
        pandascore_id=1,
        edition=edition,
        name="TBD",
        status="finished",
        begin_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    with respx.mock(assert_all_called=False) as router:
        cargo_router(router, [])
        LeaguepediaEnrichWorker().run()
    match.refresh_from_db()
    assert match.leaguepedia_synced_at is not None


@freeze_time(NOW)
def test_rate_limit_interrompe_l_intero_ciclo():
    edition = EditionFactory(competition=Competition.objects.get(code="LCK"))
    first = add_match(
        edition,
        TeamFactory(),
        TeamFactory(),
        begin=datetime(2026, 8, 1, 9, tzinfo=UTC),
        winner=None,
        stats_complete=False,
    )
    second = add_match(
        edition,
        TeamFactory(),
        TeamFactory(),
        begin=datetime(2026, 8, 1, 12, tzinfo=UTC),
        winner=None,
        stats_complete=False,
    )
    with respx.mock(assert_all_called=False) as router:
        cargo_router(router, [load("leaguepedia/ratelimited.json")])
        report = LeaguepediaEnrichWorker().run()
    assert report["rate_limited"] and report["processed"] == 0
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.leaguepedia_checked_at is None and second.leaguepedia_checked_at is None
    state = ProviderSyncState.objects.get(provider="LEAGUEPEDIA", competition=edition.competition)
    assert state.status == "FAILED" and "ratelimited" in state.last_error


@freeze_time("2026-11-14T15:00:00Z")
def test_worlds_bo1_e_bo5():
    worlds = Competition.objects.get(code="WORLDS")
    edition = CompetitionEdition.objects.create(
        competition=worlds,
        year=2026,
        name="Worlds 2026",
        starts_at=datetime(2026, 10, 15, tzinfo=UTC),
        is_active=True,
    )
    gen, tl, t1 = TeamFactory(name="Gen.G"), TeamFactory(name="Team Liquid"), TeamFactory(name="T1")
    bo1 = add_match(
        edition,
        gen,
        tl,
        begin=datetime(2026, 10, 23, 7, tzinfo=UTC),
        winner=gen,
        score=(1, 0),
        stats_complete=False,
    )
    bo5 = add_match(
        edition,
        gen,
        t1,
        begin=datetime(2026, 11, 14, 8, tzinfo=UTC),
        winner=gen,
        score=(3, 1),
        stats_complete=False,
    )
    with respx.mock(assert_all_called=False) as router:
        cargo_router(
            router,
            [
                load("leaguepedia/worlds_bo5_games.json"),
                {"cargoquery": []},
                load("leaguepedia/worlds_bo1_games.json"),
                {"cargoquery": []},
            ],
        )
        LeaguepediaEnrichWorker().run()
    assert bo5.games.count() == 4 and bo1.games.count() == 1
    assert [g.winner_team.name for g in bo5.games.order_by("game_number")] == [
        "Gen.G",
        "T1",
        "Gen.G",
        "Gen.G",
    ]


# --------------------------------------------------------------------------- endpoint 5.3
@freeze_time(NOW)
def test_feed_partite_parametri_stale_e_cache(api):
    _lck_ready()
    response = api.get("/api/esports/matches?competition=lck&state=results&limit=10")
    assert response.status_code == 200
    assert response["Cache-Control"] == "public, max-age=60, stale-while-revalidate=300"
    body = response.json()
    assert body["source"] == "PandaScore" and body["refreshIntervalMinutes"] == 60
    assert body["verificationRequired"] is True and body["stale"] is False and body["lastSyncedAt"]
    assert [m["pandascoreId"] for m in body["items"]] == [1100001, 1100002]
    assert body["items"][0]["teams"][0]["name"] == "Gen.G"
    upcoming = api.get("/api/esports/matches?state=upcoming").json()
    assert [m["pandascoreId"] for m in upcoming["items"]] == [1100010]
    assert api.get("/api/esports/matches?state=live").json()["items"] == []
    for bad in ("competition=lcs", "state=past", "limit=0", "limit=101", "limit=abc"):
        error = api.get(f"/api/esports/matches?{bad}")
        assert error.status_code == 400
        assert error.json()["message"] == "Errore di validazione dei dati"
    with freeze_time(datetime(2026, 8, 2, 12, tzinfo=UTC) + timedelta(minutes=91)):
        assert api.get("/api/esports/matches").json()["stale"] is True


@freeze_time(NOW)
def test_box_score_con_attribuzione_cc_by_sa(api):
    _, match = _lck_ready()
    with respx.mock(assert_all_called=False) as router:
        cargo_router(router, [load("leaguepedia/lck_games.json"), load("leaguepedia/lck_players.json")])
        LeaguepediaEnrichWorker().run(limit=1)
    response = api.get(f"/api/esports/matches/{match.id}/games")
    assert response["Cache-Control"] == "public, max-age=300, stale-while-revalidate=600"
    body = response.json()
    assert body["source"] == "Leaguepedia" and "CC BY-SA" in body["attribution"]
    assert "lol.fandom.com/wiki/LCK/2026_Season/Rounds_3-5" in body["attribution"]
    assert len(body["items"]) == 3 and len(body["items"][0]["players"]) == 10
    assert body["items"][0]["players"][0]["fantasyScore"] is not None
    assert api.get("/api/esports/matches/999999/games").status_code == 404


def test_feed_vuoto_e_stale_senza_sync(api):
    body = api.get("/api/esports/matches").json()
    assert body["items"] == [] and body["stale"] is True and body["lastSyncedAt"] is None


def test_team_non_eliminabile_o_inesistente(admin_client):
    team = ProTeam.objects.create(name="Solo")
    assert admin_client.delete(f"/api/teams/{team.id}").status_code == 204
    assert admin_client.delete("/api/teams/12345").status_code == 404
