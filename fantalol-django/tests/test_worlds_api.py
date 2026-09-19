"""Contratti REST della modalità Worlds sotto `/api/worlds/`."""
from datetime import timedelta

import pytest
from django.utils import timezone

from teams.models import ROLE_ORDER, Competition
from worlds.models import WorldsRosterEntry

from .factories import (
    ProPlayerFactory,
    ProTeamFactory,
    WorldsEditionFactory,
    WorldsLeagueFactory,
    WorldsStageFactory,
    WorldsTeamFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def worlds_open(settings):
    """Apre la sezione Worlds per i test di questo file.

    Qui si verifica la modalità in sé; il gating "in fase di sviluppo" ha i
    suoi test dedicati in fondo al file.
    """
    settings.FANTALOL = {**settings.FANTALOL, "WORLDS_IN_DEVELOPMENT": False}


@pytest.fixture
def worlds_in_development(settings):
    settings.FANTALOL = {**settings.FANTALOL, "WORLDS_IN_DEVELOPMENT": True}


@pytest.fixture
def edition():
    edition = WorldsEditionFactory(nome="Worlds 2026", anno=2026)
    edition.qualified_teams.set([
        ProTeamFactory(nome="G2 Esports", competition=Competition.LEC),
        ProTeamFactory(nome="T1", competition=Competition.LCK),
    ])
    return edition


def pool_for(edition):
    players = []
    for pro_team in edition.qualified_teams.all():
        players += [ProPlayerFactory(team=pro_team, ruolo=role.value,
                                     competition=pro_team.competition, quotazione=20)
                    for role in ROLE_ORDER]
    return players


def test_editions_list_exposes_stages_and_qualified_teams(auth, user, edition):
    WorldsStageFactory(edition=edition, nome="Swiss", ordine=1)
    response = auth(user).get("/api/worlds/editions/")
    assert response.status_code == 200
    payload = response.data[0]
    assert payload["nome"] == "Worlds 2026"
    assert [stage["nome"] for stage in payload["stages"]] == ["Swiss"]
    assert {team["nome"] for team in payload["qualifiedTeams"]} == {"G2 Esports", "T1"}


def test_stages_endpoint_reports_the_current_stage(auth, user, edition):
    WorldsStageFactory(edition=edition, nome="Play-In", ordine=1,
                       lineup_deadline=timezone.now() - timedelta(days=1))
    upcoming = WorldsStageFactory(edition=edition, nome="Swiss", ordine=2,
                                  lineup_deadline=timezone.now() + timedelta(days=1))
    response = auth(user).get(f"/api/worlds/editions/{edition.id}/stages/")
    assert response.status_code == 200
    assert response.data["currentStageId"] == upcoming.id
    assert [s["nome"] for s in response.data["stages"]] == ["Play-In", "Swiss"]


def test_pool_endpoint_returns_players_from_every_region(auth, user, edition):
    pool_for(edition)
    response = auth(user).get(f"/api/worlds/editions/{edition.id}/pool/")
    assert response.status_code == 200
    assert len(response.data) == 10
    assert {row["competition"] for row in response.data} == {"LEC", "LCK"}


def test_sync_pool_is_admin_only(auth, user, admin_user, edition):
    pool_for(edition)
    assert auth(user).post(f"/api/worlds/editions/{edition.id}/sync-pool/").status_code == 403
    response = auth(admin_user).post(f"/api/worlds/editions/{edition.id}/sync-pool/")
    assert response.status_code == 200
    assert response.data["playersMarked"] == 10


def test_create_league_uses_the_edition_defaults(auth, user, edition):
    response = auth(user).post("/api/worlds/leagues/",
                               {"nome": "Mondiale fra amici", "editionId": edition.id},
                               format="json")
    assert response.status_code == 201
    assert response.data["creditiIniziali"] == edition.default_crediti
    assert response.data["rosterSize"] == 10
    assert response.data["maxPerRole"] == 2
    assert response.data["allowReentrySwap"] is True
    assert response.data["mvpBonus"] == 3.0
    assert response.data["seriesWinBonus"] == 1.0


def test_create_league_accepts_overrides(auth, user, edition):
    response = auth(user).post("/api/worlds/leagues/", {
        "nome": "Custom", "editionId": edition.id, "creditiIniziali": 300,
        "rosterSize": 5, "maxPerRole": 1, "allowReentrySwap": False, "mvpBonus": 0.0,
    }, format="json")
    assert response.status_code == 201
    assert response.data["rosterSize"] == 5
    assert response.data["allowReentrySwap"] is False
    assert response.data["mvpBonus"] == 0.0


def test_join_worlds_league_with_invite_code(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition)
    response = auth(user).post("/api/worlds/leagues/join/",
                               {"codiceInvito": league.codice_invito,
                                "nomeSquadra": "Mondiali"}, format="json")
    assert response.status_code == 201
    assert response.data["creditiResidui"] == league.crediti_iniziali
    assert response.data["rosa"] == []


def test_join_is_closed_once_the_auction_started(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition, auction_open=True)
    response = auth(user).post("/api/worlds/leagues/join/",
                               {"codiceInvito": league.codice_invito,
                                "nomeSquadra": "Tardi"}, format="json")
    assert response.status_code == 400
    assert "non è più possibile iscriversi" in response.data["message"]


def test_outsiders_cannot_read_a_worlds_league(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition)
    assert auth(user).get(f"/api/worlds/leagues/{league.id}/").status_code == 403


def test_lineup_endpoint_confirms_the_current_stage_formation(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition)
    team = WorldsTeamFactory(league=league, owner=user)
    stage = WorldsStageFactory(edition=edition, ordine=1,
                               lineup_deadline=timezone.now() + timedelta(hours=6))
    players = pool_for(edition)
    for player in players:
        WorldsRosterEntry.objects.create(fanta_team=team, player=player, crediti_spesi=20)
    titolari = players[:5]

    client = auth(user)
    response = client.post(f"/api/worlds/leagues/{league.id}/lineup/", {
        "fantaTeamId": team.id, "titolariIds": [p.id for p in titolari],
    }, format="json")
    assert response.status_code == 201
    assert response.data["confirmed"] is True
    assert response.data["stageId"] == stage.id
    assert len(response.data["titolari"]) == 5

    current = client.get(f"/api/worlds/leagues/{league.id}/lineup/")
    assert current.status_code == 200
    assert current.data["lineup"]["confirmed"] is True
    assert len(current.data["roster"]) == 10


def test_lineup_endpoint_requires_a_team_in_the_league(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition, admin=user)
    WorldsStageFactory(edition=edition, ordine=1)
    response = auth(user).get(f"/api/worlds/leagues/{league.id}/lineup/")
    assert response.status_code == 400
    assert "non hai una squadra" in response.data["message"].lower()


def test_standings_endpoint_lists_teams_with_attribution(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition, admin=user)
    WorldsStageFactory(edition=edition, nome="Swiss", ordine=1)
    WorldsTeamFactory(league=league, nome="Alfa")
    response = auth(user).get(f"/api/worlds/leagues/{league.id}/standings/")
    assert response.status_code == 200
    assert response.data["edition"] == "Worlds 2026"
    assert response.data["items"][0]["teamNome"] == "Alfa"
    assert "Leaguepedia" in response.data["attribution"]


def test_swap_endpoint_replaces_a_player(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition, allow_reentry_swap=True)
    team = WorldsTeamFactory(league=league, owner=user, crediti_residui=200)
    WorldsStageFactory(edition=edition, ordine=1,
                       lineup_deadline=timezone.now() + timedelta(hours=6))
    players = pool_for(edition)
    for player in players:
        WorldsRosterEntry.objects.create(fanta_team=team, player=player, crediti_spesi=20)
    outgoing = players[0]
    incoming = ProPlayerFactory(team=edition.qualified_teams.first(),
                                ruolo=outgoing.ruolo, quotazione=25)

    response = auth(user).post(f"/api/worlds/leagues/{league.id}/swap/", {
        "fantaTeamId": team.id, "outPlayerId": outgoing.id, "inPlayerId": incoming.id,
    }, format="json")
    assert response.status_code == 200
    assert response.data["creditiResidui"] == 175
    active = [row["nickname"] for row in response.data["rosa"] if not row["released"]]
    assert incoming.nickname in active and outgoing.nickname not in active


def test_auction_endpoints_drive_a_worlds_bid(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition, admin=user, auction_open=True)
    first = WorldsTeamFactory(league=league, owner=user, crediti_residui=500)
    second = WorldsTeamFactory(league=league, crediti_residui=500)
    player = pool_for(edition)[0]

    client = auth(user)
    started = client.post(f"/api/worlds/leagues/{league.id}/auction/",
                          {"playerId": player.id, "fantaTeamId": first.id}, format="json")
    assert started.status_code == 201
    assert started.data["currentBid"] == player.quotazione

    active = client.get(f"/api/worlds/leagues/{league.id}/auction/")
    assert active.data["id"] == started.data["id"]

    # Il miglior offerente non può rilanciare su sé stesso.
    same = client.post(f"/api/worlds/auctions/{started.data['id']}/bids/",
                       {"fantaTeamId": first.id, "credits": 999}, format="json")
    assert same.status_code == 400
    assert "miglior offerente" in same.data["message"]

    # Un admin di lega può offrire per un'altra squadra solo se ne è proprietario.
    other = client.post(f"/api/worlds/auctions/{started.data['id']}/bids/",
                        {"fantaTeamId": second.id, "credits": 999}, format="json")
    assert other.status_code == 400


def test_recompute_endpoint_is_reserved_to_the_league_admin(auth, user, edition):
    league = WorldsLeagueFactory(edition=edition, admin=user)
    WorldsTeamFactory(league=league)
    response = auth(user).post(f"/api/worlds/leagues/{league.id}/recompute/")
    assert response.status_code == 200
    assert response.data["recomputed"] == 0


# --- sezione in fase di sviluppo -----------------------------------------
def test_worlds_is_closed_to_regular_users_while_in_development(
        auth, user, edition, worlds_in_development):
    """Con il flag attivo ogni rotta Worlds risponde 403 a un utente normale."""
    league = WorldsLeagueFactory(edition=edition, admin=user)
    WorldsStageFactory(edition=edition, ordine=1)
    client = auth(user)

    closed = [
        ("get", "/api/worlds/editions/"),
        ("get", f"/api/worlds/editions/{edition.id}/"),
        ("get", f"/api/worlds/editions/{edition.id}/stages/"),
        ("get", f"/api/worlds/editions/{edition.id}/pool/"),
        ("get", "/api/worlds/leagues/"),
        ("post", "/api/worlds/leagues/"),
        ("post", "/api/worlds/leagues/join/"),
        ("get", f"/api/worlds/leagues/{league.id}/"),
        ("get", f"/api/worlds/leagues/{league.id}/teams/"),
        ("get", f"/api/worlds/leagues/{league.id}/lineup/"),
        ("post", f"/api/worlds/leagues/{league.id}/lineup/"),
        ("get", f"/api/worlds/leagues/{league.id}/standings/"),
        ("post", f"/api/worlds/leagues/{league.id}/swap/"),
        ("post", f"/api/worlds/leagues/{league.id}/recompute/"),
        ("get", f"/api/worlds/leagues/{league.id}/auction/"),
    ]
    for method, path in closed:
        response = getattr(client, method)(path, {}, format="json")
        assert response.status_code == 403, f"{method.upper()} {path} -> {response.status_code}"
        assert "in fase di sviluppo" in response.data["message"]


def test_worlds_stays_open_to_the_admin_while_in_development(
        auth, admin_user, edition, worlds_in_development):
    client = auth(admin_user)
    assert client.get("/api/worlds/editions/").status_code == 200
    assert client.get(f"/api/worlds/editions/{edition.id}/stages/").status_code == 200
    assert client.get("/api/worlds/leagues/").status_code == 200


def test_worlds_reopens_to_everyone_when_the_flag_is_off(auth, user, edition):
    # La fixture autouse ha già spento WORLDS_IN_DEVELOPMENT.
    assert auth(user).get("/api/worlds/editions/").status_code == 200


def test_status_endpoint_tells_regular_users_the_section_is_in_development(
        auth, user, worlds_in_development):
    response = auth(user).get("/api/worlds/status/")
    assert response.status_code == 200
    assert response.data["inDevelopment"] is True
    assert response.data["accessible"] is False
    assert "in fase di sviluppo" in response.data["message"]


def test_status_endpoint_marks_the_section_accessible_for_the_admin(
        auth, admin_user, worlds_in_development):
    response = auth(admin_user).get("/api/worlds/status/")
    assert response.data["inDevelopment"] is True
    assert response.data["accessible"] is True


def test_status_endpoint_requires_authentication(api):
    assert api.get("/api/worlds/status/").status_code == 401
