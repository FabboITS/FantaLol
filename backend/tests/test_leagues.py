"""Porting di LeagueVisibilityServiceTest, LeagueAuctionPhaseServiceTest, LeagueRosterCompletionTest,
FantaTeamServiceTest e dei test di contratto delle API delle leghe."""

import pytest

from apps.common.exceptions import AccessDeniedException, BusinessRuleException, ResourceNotFoundException
from apps.competitions.models import Competition
from apps.leagues import services
from apps.leagues.models import AuctionSession, AuctionStatus, FantaTeam, League, RosterEntry

from .factories import (
    AdminFactory,
    EditionFactory,
    FantaTeamFactory,
    LeagueFactory,
    UserFactory,
    build_edition_rosters,
    give_roster,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def lec():
    edition = EditionFactory()
    rosters = build_edition_rosters(edition, 10)
    return edition, [e for entries in rosters.values() for e in entries]


# --------------------------------------------------------------------------- visibilità
def test_admin_globale_vede_tutte_le_leghe_utente_solo_le_sue_senza_duplicati(lec):
    alice, bob = UserFactory(username="alice"), UserFactory(username="bob")
    created = LeagueFactory(admin=alice, edition=lec[0])
    joined = LeagueFactory(admin=bob, edition=lec[0])
    FantaTeamFactory(league=joined, owner=alice)
    FantaTeamFactory(league=created, owner=alice)
    LeagueFactory(admin=bob, edition=lec[0])
    assert [league.id for league in services.accessible_leagues(AdminFactory())] == list(
        League.objects.order_by("id").values_list("id", flat=True))
    assert [league.id for league in services.accessible_leagues(alice)] == [created.id, joined.id]


def test_creatore_e_iscritto_aprono_la_lega_estraneo_no(lec, api):
    alice, bob, eve = UserFactory(), UserFactory(), UserFactory()
    league = LeagueFactory(admin=alice, edition=lec[0])
    FantaTeamFactory(league=league, owner=bob)
    services.assert_can_view(alice, league)
    services.assert_can_view(bob, league)
    with pytest.raises(AccessDeniedException):
        services.assert_can_view(eve, league)
    from .conftest import auth_client

    assert auth_client(eve).get(f"/api/leagues/{league.id}").status_code == 403
    assert auth_client(eve).get(f"/api/fanta-teams/by-league/{league.id}").status_code == 403


def test_eliminazione_lega(lec):
    alice, eve = UserFactory(), UserFactory()
    league = LeagueFactory(admin=alice, edition=lec[0])
    with pytest.raises(AccessDeniedException):
        services.delete_league(eve, league.id)
    services.delete_league(AdminFactory(), league.id)
    assert not League.objects.filter(pk=league.id).exists()
    with pytest.raises(ResourceNotFoundException):
        services.delete_league(alice, league.id)


# --------------------------------------------------------------------------- fase d'asta
def test_creatore_apre_chiude_e_riapre_l_asta(lec):
    creator = UserFactory()
    league = LeagueFactory(admin=creator, edition=lec[0], participant_count=4)
    assert services.open_auction(creator, league.id).auction_open
    assert not services.close_auction(creator, league.id).auction_open
    assert services.open_auction(creator, league.id).auction_open


def test_partecipante_non_apre_l_asta_e_serve_una_giornata(lec):
    creator, other = UserFactory(), UserFactory()
    league = LeagueFactory(admin=creator, edition=lec[0])
    with pytest.raises(BusinessRuleException, match="Solo il creatore della lega può gestire l'asta"):
        services.open_auction(other, league.id)
    with pytest.raises(BusinessRuleException, match="giornata"):
        services.open_auction(creator, league.id)


def test_chiusura_rifiutata_con_asta_player_attiva(lec):
    creator = UserFactory()
    league = LeagueFactory(admin=creator, edition=lec[0], participant_count=2, auction_open=True)
    from django.utils import timezone

    AuctionSession.objects.create(league=league, player=lec[1][0].player, current_bid=10,
                                  ends_at=timezone.now(), status=AuctionStatus.ACTIVE)
    with pytest.raises(BusinessRuleException,
                       match="Attendi la fine dell'asta del player prima di terminare l'asta della lega"):
        services.close_auction(creator, league.id)
    league.refresh_from_db()
    assert league.auction_open


# --------------------------------------------------------------------------- completamento casuale
def test_creatore_completa_ogni_ruolo_mancante(lec):
    creator = UserFactory()
    league = LeagueFactory(admin=creator, edition=lec[0], participant_count=1)
    team = FantaTeamFactory(league=league, owner=creator)
    result = services.complete_all_rosters_randomly(creator, league.id)
    assert len(result) == 1
    response = services.fanta_team_response(result[0])
    assert len(response["rosa"]) == 10
    assert all(entry["crediti_spesi"] == 0 for entry in response["rosa"])
    assert response["punti"] is None
    roles = sorted(e["ruolo"] for e in response["rosa"])
    assert roles == sorted(["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"] * 2)
    assert team.rosa.count() == 10


def test_completamento_rifiutato_ad_asta_aperta(lec):
    creator = UserFactory()
    league = LeagueFactory(admin=creator, edition=lec[0], auction_open=True)
    with pytest.raises(BusinessRuleException,
                       match="Termina l'asta della lega prima di completare casualmente le rose"):
        services.complete_all_rosters_randomly(creator, league.id)


# --------------------------------------------------------------------------- FantaTeam
def test_iscrizione_e_limiti(lec):
    owner = UserFactory()
    league = LeagueFactory(edition=lec[0], crediti_iniziali=500)
    team = services.join_league(owner, league.codice_invito, "I Signori del Rift")
    assert team.nome == "I Signori del Rift" and team.crediti_residui == 500
    with pytest.raises(BusinessRuleException, match="già iscritto"):
        services.join_league(owner, league.codice_invito, "Altra")
    with pytest.raises(BusinessRuleException, match="Nessuna lega trovata"):
        services.join_league(owner, "XXXX", "Altra")
    for _ in range(9):
        FantaTeamFactory(league=league)
    with pytest.raises(BusinessRuleException, match="La lega ha già raggiunto il limite di 10 squadre"):
        services.join_league(UserFactory(), league.codice_invito, "Undicesima")


def test_niente_iscrizioni_dopo_la_prima_giornata(lec):
    league = LeagueFactory(edition=lec[0], participant_count=2)
    with pytest.raises(BusinessRuleException, match="iniziata"):
        services.join_league(UserFactory(), league.codice_invito, "Tardi")


def test_acquisto_diretto(lec):
    owner = UserFactory()
    league = LeagueFactory(edition=lec[0])
    team = FantaTeamFactory(league=league, owner=owner, crediti_residui=500)
    player = lec[1][0]  # quotazione 10
    entry = services.buy_player(owner, team.id, player.player_id, 90)
    team.refresh_from_db()
    assert entry.crediti_spesi == 90 and team.crediti_residui == 410
    with pytest.raises(BusinessRuleException, match="Crediti insufficienti"):
        services.buy_player(owner, team.id, lec[1][1].player_id, 900)
    with pytest.raises(BusinessRuleException, match="inferiore alla quotazione"):
        services.buy_player(owner, team.id, lec[1][1].player_id, 1)
    other = FantaTeamFactory(league=league)
    with pytest.raises(BusinessRuleException, match="già stato acquistato"):
        services.buy_player(other.owner, other.id, player.player_id, 100)
    with pytest.raises(BusinessRuleException, match="proprietario"):
        services.buy_player(UserFactory(), team.id, lec[1][2].player_id, 100)


def test_rilascio_con_rimborso_del_cinquanta_per_cento(lec, user_client, user):
    league = LeagueFactory(edition=lec[0])
    team = FantaTeamFactory(league=league, owner=user, crediti_residui=100)
    entry = give_roster(team, lec[1][:1], credits=31)[0]
    assert user_client.delete(f"/api/fanta-teams/{team.id}/rosa/{entry.id}").status_code == 204
    team.refresh_from_db()
    assert team.crediti_residui == 115 and not RosterEntry.objects.filter(pk=entry.pk).exists()


def test_player_gratis_solo_se_le_altre_rose_sono_complete(lec):
    owner = UserFactory()
    league = LeagueFactory(edition=lec[0], participant_count=6)
    team = FantaTeamFactory(league=league, owner=owner, crediti_residui=0)
    other = FantaTeamFactory(league=league)
    with pytest.raises(BusinessRuleException, match="tutte le altre squadre"):
        services.free_player(owner, team.id)
    give_roster(other, [e for e in lec[1] if e.team == lec[1][5].team])
    entry = services.free_player(owner, team.id)
    assert entry.crediti_spesi == 0
    team.crediti_residui = 1000
    team.save()
    with pytest.raises(BusinessRuleException, match="abbastanza crediti"):
        services.free_player(owner, team.id)


def test_esclusivita_vale_solo_per_le_leghe_regionali(lec):
    league = LeagueFactory(edition=lec[0])
    a, b = FantaTeamFactory(league=league), FantaTeamFactory(league=league)
    give_roster(a, lec[1][:1])
    with pytest.raises(BusinessRuleException):
        services.add_roster_entry(b, lec[1][0].player, 10)
    worlds_edition = EditionFactory(competition=Competition.objects.get(code="WORLDS"))
    worlds = LeagueFactory(edition=worlds_edition)
    c, d = FantaTeamFactory(league=worlds), FantaTeamFactory(league=worlds)
    services.add_roster_entry(c, lec[1][0].player, 10)
    services.add_roster_entry(d, lec[1][0].player, 10)
    assert RosterEntry.objects.filter(league=worlds, player=lec[1][0].player).count() == 2


# --------------------------------------------------------------------------- API e contratto JSON
LEAGUE_KEYS = {"id", "nome", "codiceInvito", "creditiIniziali", "adminUsername", "numeroSquadre", "auctionOpen",
               "participantCount", "competitionStarted", "maxRosterSize", "maxPerRole"}
TEAM_KEYS = {"id", "nome", "creditiResidui", "leagueId", "leagueNome", "ownerUsername", "punti", "rosa"}
ENTRY_KEYS = {"id", "lecPlayerId", "lecPlayerNickname", "ruolo", "creditiSpesi", "dataAcquisto"}


def test_contratto_api_leghe_e_fanta_team(lec, user, user_client):
    created = user_client.post("/api/leagues", {"nome": "Lega API", "creditiIniziali": 700, "competition": "lec"},
                               format="json")
    assert created.status_code == 201
    body = created.json()
    assert LEAGUE_KEYS <= set(body)
    assert body["competition"] == "LEC" and body["ruleset"] == "REGIONAL" and body["creditiIniziali"] == 700
    assert body["maxRosterSize"] == 10 and body["maxPerRole"] == 2 and body["maxParticipants"] == 10
    joined = user_client.post("/api/fanta-teams/join", {"codiceInvito": body["codiceInvito"],
                                                        "nomeSquadra": "Blue"}, format="json")
    assert joined.status_code == 201 and TEAM_KEYS <= set(joined.json())
    team_id = joined.json()["id"]
    give_roster(FantaTeam.objects.get(pk=team_id), lec[1][:1], credits=12)
    entry = user_client.get(f"/api/fanta-teams/{team_id}").json()["rosa"][0]
    assert ENTRY_KEYS <= set(entry)
    assert [t["id"] for t in user_client.get("/api/fanta-teams/me").json()] == [team_id]
    assert user_client.get(f"/api/fanta-teams/by-league/{body['id']}").status_code == 200
    assert user_client.get(f"/api/leagues/{body['id']}").json()["numeroSquadre"] == 1
    assert [league["id"] for league in user_client.get("/api/leagues").json()] == [body["id"]]
    assert user_client.delete(f"/api/leagues/{body['id']}").status_code == 204


def test_validazione_creazione_lega(user_client, lec):
    response = user_client.post("/api/leagues", {"nome": "", "creditiIniziali": -1}, format="json")
    assert response.status_code == 400
    assert "creditiIniziali: I crediti iniziali devono essere positivi" in response.json()["details"]
    missing = user_client.post("/api/leagues", {"nome": "X"}, format="json")
    assert missing.status_code == 422
    assert user_client.post("/api/leagues", {"nome": "X", "competition": "LPL"}, format="json").status_code == 422
    assert user_client.post("/api/leagues", {"nome": "X", "editionId": 999}, format="json").status_code == 404


def test_lega_worlds_usa_budget_e_impostazioni_di_default(user_client):
    edition = EditionFactory(competition=Competition.objects.get(code="WORLDS"))
    body = user_client.post("/api/leagues", {"nome": "Worlds", "editionId": edition.id}, format="json").json()
    assert body["ruleset"] == "WORLDS" and body["creditiIniziali"] == 100
    assert body["settings"]["freeTransfersPerMatchday"] == 2 and body["maxParticipants"] == 50
    assert body["maxRosterSize"] == 8 and body["maxPerRole"] is None
    exclusive = user_client.post("/api/leagues", {"nome": "W2", "editionId": edition.id,
                                                  "settings": {"worlds_exclusive": True}}, format="json")
    assert exclusive.status_code == 422


def test_completamento_e_fasi_asta_via_api(lec, user, user_client):
    league = LeagueFactory(admin=user, edition=lec[0], participant_count=1)
    FantaTeamFactory(league=league, owner=user)
    assert user_client.put(f"/api/leagues/{league.id}/auction/open").json()["auctionOpen"] is True
    assert user_client.put(f"/api/leagues/{league.id}/auction/close").json()["auctionOpen"] is False
    response = user_client.post(f"/api/leagues/{league.id}/rosters/complete-randomly")
    assert response.status_code == 200 and len(response.json()[0]["rosa"]) == 10
