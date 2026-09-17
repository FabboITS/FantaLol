"""Flusso end-to-end di una lega stagionale attraverso le API REST."""
import pytest

from leagues.models import AuctionStatus
from teams.models import ROLE_ORDER

from .factories import ProPlayerFactory, ProTeamFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def pool():
    pro_team = ProTeamFactory()
    return [ProPlayerFactory(team=pro_team, ruolo=role.value, quotazione=20)
            for role in ROLE_ORDER]


def test_full_league_lifecycle_through_the_api(api, auth, pool):
    owner = UserFactory(password="password123")
    rival = UserFactory(password="password123")

    client = auth(owner)
    league = client.post("/api/leagues", {"nome": "Coppa"}, format="json").data
    my_team = client.post("/api/fanta-teams/join",
                          {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Alfa"},
                          format="json").data

    rival_client = auth(rival)
    rival_team = rival_client.post("/api/fanta-teams/join",
                                   {"codiceInvito": league["codiceInvito"],
                                    "nomeSquadra": "Beta"}, format="json").data

    # La prima giornata avvia la competizione e apre l'asta.
    client = auth(owner)
    matchday = client.post("/api/matchdays",
                           {"leagueId": league["id"], "numero": 1, "descrizione": "Prima"},
                           format="json")
    assert matchday.status_code == 201
    assert matchday.data["auctionLocked"] is True

    refreshed = client.get(f"/api/leagues/{league['id']}").data
    assert refreshed["competitionStarted"] is True
    assert refreshed["participantCount"] == 2
    assert refreshed["auctionOpen"] is True

    # Asta: apertura alla quotazione, rilancio dell'avversario.
    auction = client.post("/api/auctions", {
        "leagueId": league["id"], "lecPlayerId": pool[0].id,
        "fantaTeamId": my_team["id"],
    }, format="json")
    assert auction.status_code == 201
    assert auction.data["currentBid"] == 20
    assert auction.data["status"] == AuctionStatus.ACTIVE

    rival_client = auth(rival)
    bid = rival_client.post(f"/api/auctions/{auction.data['id']}/bids",
                            {"fantaTeamId": rival_team["id"], "credits": 30}, format="json")
    assert bid.status_code == 200
    assert bid.data["highestBidderId"] == rival_team["id"]
    assert bid.data["currentBid"] == 30

    active = rival_client.get(f"/api/auctions/active?leagueId={league['id']}")
    assert active.data["id"] == auction.data["id"]

    # Chiusura dell'asta di lega: bloccata finché una singola asta è attiva.
    client = auth(owner)
    blocked = client.put(f"/api/leagues/{league['id']}/auction/close")
    assert blocked.status_code == 400
    assert "Attendi la fine" in blocked.data["message"]


def test_matchday_stats_are_admin_only_and_compute_the_fantavoto(auth, pool):
    owner = UserFactory(password="password123")
    rival = UserFactory(password="password123")
    client = auth(owner)
    league = client.post("/api/leagues", {"nome": "Stat"}, format="json").data
    client.post("/api/fanta-teams/join",
                {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Alfa"}, format="json")
    auth(rival).post("/api/fanta-teams/join",
                     {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Beta"},
                     format="json")
    client = auth(owner)
    matchday = client.post("/api/matchdays", {"leagueId": league["id"], "numero": 1},
                           format="json").data

    mid = next(p for p in pool if p.ruolo == "MID")
    created = client.post(f"/api/matchdays/{matchday['id']}/stats", {
        "lecPlayerId": mid.id, "kills": 3, "morti": 1, "assist": 5, "cs": 250,
        "visionScore": 20, "vittoria": True,
    }, format="json")
    assert created.status_code == 201
    # MID: 9 + 10 - 2 + 2.5 + 3 = 22.5
    assert created.data["fantavoto"] == pytest.approx(22.5)
    assert created.data["wins"] == 1

    # Un partecipante non admin non può inserire statistiche.
    forbidden = auth(rival).post(f"/api/matchdays/{matchday['id']}/stats",
                                 {"lecPlayerId": mid.id, "kills": 99}, format="json")
    assert forbidden.status_code == 400

    listed = auth(rival).get(f"/api/matchdays/{matchday['id']}/stats")
    assert listed.status_code == 200
    assert listed.data[0]["lecPlayerNickname"] == mid.nickname


def test_matchday_close_endpoint_marks_the_matchday_closed(auth):
    owner = UserFactory(password="password123")
    rival = UserFactory(password="password123")
    client = auth(owner)
    league = client.post("/api/leagues", {"nome": "Chiusura"}, format="json").data
    client.post("/api/fanta-teams/join",
                {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Alfa"}, format="json")
    auth(rival).post("/api/fanta-teams/join",
                     {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Beta"},
                     format="json")
    client = auth(owner)
    matchday = client.post("/api/matchdays", {"leagueId": league["id"], "numero": 1},
                           format="json").data

    closed = client.post(f"/api/matchdays/{matchday['id']}/chiudi")
    assert closed.status_code == 200
    assert closed.data["chiusa"] is True
    assert closed.data["status"] == "CLOSED"

    waiting = client.post(f"/api/matchdays/{matchday['id']}/waiting-for-postponed")
    assert waiting.status_code == 400


def test_matchdays_list_is_scoped_to_visible_leagues(auth, pool):
    owner = UserFactory(password="password123")
    outsider = UserFactory(password="password123")
    rival = UserFactory(password="password123")
    client = auth(owner)
    league = client.post("/api/leagues", {"nome": "Privata"}, format="json").data
    client.post("/api/fanta-teams/join",
                {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Alfa"}, format="json")
    auth(rival).post("/api/fanta-teams/join",
                     {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Beta"},
                     format="json")
    auth(owner).post("/api/matchdays", {"leagueId": league["id"], "numero": 1}, format="json")

    assert len(auth(owner).get("/api/matchdays").data) == 1
    assert auth(outsider).get("/api/matchdays").data == []


def test_league_deletion_is_reserved_to_its_creator(auth):
    owner = UserFactory(password="password123")
    stranger = UserFactory(password="password123")
    league = auth(owner).post("/api/leagues", {"nome": "Mia"}, format="json").data

    assert auth(stranger).delete(f"/api/leagues/{league['id']}").status_code == 403
    assert auth(owner).delete(f"/api/leagues/{league['id']}").status_code == 204


def test_my_teams_endpoint_lists_only_owned_teams(auth):
    owner = UserFactory(password="password123")
    other = UserFactory(password="password123")
    league = auth(owner).post("/api/leagues", {"nome": "Lista"}, format="json").data
    auth(owner).post("/api/fanta-teams/join",
                     {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Alfa"},
                     format="json")
    auth(other).post("/api/fanta-teams/join",
                     {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Beta"},
                     format="json")

    mine = auth(owner).get("/api/fanta-teams/me")
    assert [row["nome"] for row in mine.data] == ["Alfa"]


def test_roster_purchase_and_release_through_the_api(auth, pool):
    owner = UserFactory(password="password123")
    client = auth(owner)
    league = client.post("/api/leagues", {"nome": "Rosa", "creditiIniziali": 200},
                         format="json").data
    team = client.post("/api/fanta-teams/join",
                       {"codiceInvito": league["codiceInvito"], "nomeSquadra": "Alfa"},
                       format="json").data

    bought = client.post(f"/api/fanta-teams/{team['id']}/rosa",
                         {"lecPlayerId": pool[0].id, "creditiOfferti": 40}, format="json")
    assert bought.status_code == 201
    assert bought.data["creditiSpesi"] == 40

    detail = client.get(f"/api/fanta-teams/{team['id']}")
    assert detail.data["creditiResidui"] == 160

    released = client.delete(f"/api/fanta-teams/{team['id']}/rosa/{bought.data['id']}")
    assert released.status_code == 204
    assert client.get(f"/api/fanta-teams/{team['id']}").data["creditiResidui"] == 180


def test_teams_by_league_requires_membership(auth):
    owner = UserFactory(password="password123")
    stranger = UserFactory(password="password123")
    league = auth(owner).post("/api/leagues", {"nome": "Chiusa"}, format="json").data
    assert auth(stranger).get(f"/api/fanta-teams/by-league/{league['id']}").status_code == 403
