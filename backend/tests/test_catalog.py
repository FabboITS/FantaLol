"""Porting di LecTeamServiceTest/LecPlayerServiceTest generalizzati + endpoint admin dei dati reali."""

from datetime import UTC, datetime

import pytest

from apps.competitions.models import Competition
from apps.esports.models import EditionRoster, GamePlayerStat, PlayerAlias, ProPlayer, ProTeam, TeamAlias
from apps.leagues.models import RosterEntry

from .factories import (
    EditionFactory,
    FantaTeamFactory,
    LeagueFactory,
    add_game,
    add_match,
    build_edition_rosters,
)

pytestmark = pytest.mark.django_db
PLAYER_KEYS = {
    "id",
    "nickname",
    "nomeReale",
    "nazionalita",
    "ruolo",
    "quotazione",
    "teamId",
    "teamNome",
    "imageUrl",
    "competition",
}


@pytest.fixture
def editions():
    lec = EditionFactory(name="LEC 2026")
    lck = EditionFactory(name="LCK 2026", competition=Competition.objects.get(code="LCK"))
    build_edition_rosters(lec, 2)
    build_edition_rosters(lck, 3)
    return lec, lck


def test_players_filtrati_per_competizione_edizione_ruolo_e_team(api, editions):
    lec, lck = editions
    everyone = api.get("/api/players").json()
    assert len(everyone) == 25 and PLAYER_KEYS <= set(everyone[0])
    assert {p["competition"] for p in everyone} == {"LEC", "LCK"}
    lck_players = api.get("/api/players?competition=lck").json()
    assert len(lck_players) == 15 and {p["competition"] for p in lck_players} == {"LCK"}
    assert len(api.get(f"/api/players?edition={lec.id}").json()) == 10
    mids = api.get("/api/players?competition=LCK&role=mid").json()
    assert len(mids) == 3 and {p["ruolo"] for p in mids} == {"MID"}
    assert len(api.get("/api/players?ruolo=SUPPORT").json()) == 5
    team_id = lck_players[0]["teamId"]
    assert {p["teamId"] for p in api.get(f"/api/players?teamId={team_id}").json()} == {team_id}
    assert api.get("/api/players?role=COACH").status_code == 400
    assert api.get("/api/players?competition=xyz").status_code == 404
    assert api.get("/api/players?edition=999").status_code == 404


def test_teams_per_competizione_con_players_e_logo(api, editions):
    teams = api.get("/api/teams?competition=LCK").json()
    assert len(teams) == 3
    first = teams[0]
    assert set(first) >= {"id", "nome", "sigla", "logoUrl", "players", "competition"}
    assert len(first["players"]) == 5 and [p["ruolo"] for p in first["players"]] == [
        "TOP",
        "JUNGLE",
        "MID",
        "ADC",
        "SUPPORT",
    ]
    assert len(api.get("/api/teams").json()) == 5
    detail = api.get(f"/api/teams/{first['id']}").json()
    assert detail["nome"] == first["nome"] and len(detail["giocatori"]) == 5
    assert api.get("/api/teams/99999").status_code == 404


def test_logo_e_foto_locali_hanno_precedenza(api, editions):
    team = ProTeam.objects.first()
    team.image_url_light = "https://cdn/logo.png"
    team.save()
    assert team.logo_url == "https://cdn/logo.png"
    team.logo_file = "teams/x.png"
    team.save()
    assert team.logo_url == "/media/teams/x.png"
    player = ProPlayer.objects.first()
    player.image_file = "players/lec/mid/x.png"
    assert player.photo_url == "/media/players/lec/mid/x.png"


def test_crud_admin_di_team_e_player(api, admin_client, user_client, editions):
    lec, _ = editions
    payload = {"nome": "Nuovo Team", "sigla": "NT", "logoUrl": "/assets/team-logos/nt.png"}
    assert api.post("/api/teams", payload, format="json").status_code == 401
    assert user_client.post("/api/teams", payload, format="json").status_code == 403
    created = admin_client.post("/api/teams", payload, format="json")
    assert created.status_code == 201 and created.json()["logoUrl"] == "/assets/team-logos/nt.png"
    duplicate = admin_client.post("/api/teams", payload, format="json")
    assert (
        duplicate.status_code == 422
        and duplicate.json()["message"] == "Esiste già un team con nome: Nuovo Team"
    )
    team_id = created.json()["id"]
    assert (
        admin_client.put(f"/api/teams/{team_id}", {**payload, "sigla": "NTX"}, format="json").json()["sigla"]
        == "NTX"
    )
    body = {
        "nickname": "Rookie",
        "nomeReale": "Mario Rossi",
        "nazionalita": "IT",
        "ruolo": "MID",
        "quotazione": 33,
        "teamId": team_id,
        "editionId": lec.id,
    }
    assert admin_client.post("/api/players", {**body, "ruolo": None}, format="json").status_code == 400
    player = admin_client.post("/api/players", body, format="json")
    assert player.status_code == 201
    created_player = player.json()
    assert created_player["quotazione"] == 33 and created_player["competition"] == "LEC"
    updated = admin_client.put(
        f"/api/players/{created_player['id']}", {**body, "quotazione": 40, "ruolo": "TOP"}, format="json"
    ).json()
    assert updated["quotazione"] == 40 and updated["ruolo"] == "TOP"
    other_team = ProTeam.objects.exclude(pk=team_id).first()
    moved = admin_client.put(
        f"/api/players/{created_player['id']}", {**body, "teamId": other_team.id}, format="json"
    ).json()
    assert moved["teamId"] == other_team.id
    assert EditionRoster.objects.filter(player_id=created_player["id"]).count() == 2
    assert api.get(f"/api/players/{created_player['id']}").json()["nickname"] == "Rookie"
    league = LeagueFactory(edition=lec)
    team = FantaTeamFactory(league=league)
    RosterEntry.objects.create(
        fanta_team=team, league=league, player_id=created_player["id"], crediti_spesi=1
    )
    assert admin_client.delete(f"/api/players/{created_player['id']}").status_code == 422
    RosterEntry.objects.all().delete()
    assert admin_client.delete(f"/api/players/{created_player['id']}").status_code == 204
    assert admin_client.delete(f"/api/teams/{team_id}").status_code == 204


def test_player_senza_edizione_e_creazione_senza_edizione_esplicita(admin_client, api, editions):
    lonely = ProPlayer.objects.create(nickname="Free Agent")
    assert api.get(f"/api/players/{lonely.id}").json()["ruolo"] is None
    team = ProTeam.objects.filter(edition_rosters__edition__name="LCK 2026").first()
    created = admin_client.post(
        "/api/players",
        {"nickname": "Auto", "ruolo": "ADC", "quotazione": 5, "teamId": team.id},
        format="json",
    ).json()
    assert created["competition"] == "LCK"
    assert (
        admin_client.put(
            f"/api/players/{lonely.id}",
            {"nickname": "Free", "ruolo": "TOP", "quotazione": 3, "teamId": team.id},
            format="json",
        ).json()["ruolo"]
        == "TOP"
    )


def test_statistiche_non_associate_alias_e_game_manuali(admin_client, user_client, editions):
    lec, _ = editions
    a, b = ProTeam.objects.filter(edition_rosters__edition=lec).distinct()[:2]
    match = add_match(lec, a, b, begin=datetime(2026, 8, 1, 15, tzinfo=UTC), winner=a)
    game = add_game(match)
    GamePlayerStat.objects.create(
        game=game,
        leaguepedia_link="Sconosciuto",
        source_team_name=a.name,
        role="MID",
        kills=1,
        deaths=0,
        assists=0,
        cs=100,
        vision_score=10,
        win=True,
    )
    GamePlayerStat.objects.create(game=game, leaguepedia_link="MISSING:x:Top", is_complete=False)
    assert user_client.get("/api/admin/esports/unmatched-stats").status_code == 403
    rows = admin_client.get("/api/admin/esports/unmatched-stats").json()
    assert [r["leaguepediaLink"] for r in rows] == ["Sconosciuto"] and rows[0]["competition"] == "LEC"
    target = EditionRoster.objects.filter(edition=lec, team=a, role="MID").first().player
    alias = admin_client.post(
        "/api/admin/esports/aliases/player",
        {"leaguepediaLink": "Sconosciuto", "playerId": target.id},
        format="json",
    )
    assert alias.status_code == 201 and PlayerAlias.objects.get().player == target
    assert GamePlayerStat.objects.get(leaguepedia_link="Sconosciuto").player == target
    assert admin_client.get("/api/admin/esports/unmatched-stats").json() == []
    team_alias = admin_client.post(
        "/api/admin/esports/aliases/team",
        {"pandascoreName": "Nongshim Red Force", "leaguepediaName": "Nongshim RedForce", "teamId": a.id},
        format="json",
    )
    assert team_alias.status_code == 201 and TeamAlias.objects.get().team == a
    assert admin_client.post("/api/admin/esports/aliases/coach", {}, format="json").status_code == 400
    assert (
        admin_client.post(
            "/api/admin/esports/aliases/player", {"leaguepediaLink": "x", "playerId": 999}, format="json"
        ).status_code
        == 404
    )
    manual = admin_client.post(
        f"/api/admin/esports/matches/{match.id}/games", {"gameNumber": 2, "winnerTeamId": b.id}, format="json"
    )
    assert manual.status_code == 201
    assert (
        admin_client.post(
            f"/api/admin/esports/matches/{match.id}/games", {"gameNumber": 2}, format="json"
        ).status_code
        == 422
    )
    correction = admin_client.put(
        f"/api/admin/games/{manual.json()['id']}/players/{target.id}",
        {
            "kills": 3,
            "deaths": 1,
            "assists": 2,
            "cs": 210,
            "visionScore": 20,
            "win": False,
            "champion": "Azir",
        },
        format="json",
    ).json()
    assert correction["kills"] == 3 and correction["fantasyScore"] is not None
    assert admin_client.put("/api/admin/games/nope/players/1", {}, format="json").status_code == 404
    assert admin_client.delete(f"/api/admin/games/{game.id}/players/99999/override").status_code == 404


def test_cors_sulle_api(api):
    preflight = api.options(
        "/api/teams", HTTP_ORIGIN="https://fantalol.win", HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET"
    )
    assert preflight.status_code == 200
    assert preflight["Access-Control-Allow-Origin"] == "https://fantalol.win"
    response = api.get("/api/teams", HTTP_ORIGIN="https://fantalol.win")
    assert response["Access-Control-Allow-Credentials"] == "true"
    assert "Access-Control-Allow-Origin" not in api.get("/api/teams")


def test_errori_api_uniformi(api, user_client):
    missing = user_client.get("/api/leagues/99999")
    assert missing.status_code == 404 and set(missing.json()) == {
        "timestamp",
        "status",
        "error",
        "message",
        "path",
        "details",
    }
    assert missing.json()["path"] == "/api/leagues/99999"
    assert api.delete("/api/health").status_code == 405
    assert api.post("/api/auth/login", "{bad", content_type="application/json").status_code == 400
