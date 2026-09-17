"""Porting di `AuthIntegrationTest`, `FormationControllerTest`,
`CumulativeScoringControllerSecurityTest` e `AdminUserDirectoryIntegrationTest`.

Verifica che i contratti REST consumati dal frontend restino invariati.
"""
import pytest

from teams.models import ROLE_ORDER, Competition

from .factories import (
    FantaTeamFactory,
    LeagueFactory,
    ProPlayerFactory,
    ProTeamFactory,
    RosterEntryFactory,
)

pytestmark = pytest.mark.django_db


# --- auth -----------------------------------------------------------------
def test_register_returns_a_bearer_token(api):
    response = api.post("/api/auth/register",
                        {"username": "nuovo", "email": "nuovo@fantalol.test",
                         "password": "password123"}, format="json")
    assert response.status_code == 201
    assert response.data["tokenType"] == "Bearer"
    assert response.data["username"] == "nuovo"
    assert response.data["role"] == "USER"
    assert response.data["token"]


def test_register_rejects_duplicate_username(api, user):
    response = api.post("/api/auth/register",
                        {"username": user.username, "email": "altra@fantalol.test",
                         "password": "password123"}, format="json")
    assert response.status_code == 400
    assert "già in uso" in response.data["message"]


def test_register_rejects_short_password(api):
    response = api.post("/api/auth/register",
                        {"username": "corto", "email": "corto@fantalol.test",
                         "password": "123"}, format="json")
    assert response.status_code == 400


def test_login_with_wrong_credentials_is_rejected(api, user):
    response = api.post("/api/auth/login",
                        {"username": user.username, "password": "sbagliata"}, format="json")
    assert response.status_code == 400
    assert "Credenziali non valide" in response.data["message"]


def test_refresh_returns_a_new_access_token(api, user):
    login = api.post("/api/auth/login",
                     {"username": user.username, "password": "password123"}, format="json")
    response = api.post("/api/auth/refresh", {"refresh": login.data["refreshToken"]},
                        format="json")
    assert response.status_code == 200
    assert response.data["token"]


def test_me_requires_authentication(api):
    assert api.get("/api/users/me").status_code == 401


def test_me_returns_the_profile_display_name(auth, user):
    client = auth(user)
    client.put("/api/users/me/profile", {"nomeVisualizzato": "Natsu"}, format="json")
    response = client.get("/api/users/me")
    assert response.status_code == 200
    assert response.data["nomeVisualizzato"] == "Natsu"
    assert response.data["role"] == "USER"


# --- directory utenti (solo admin) ---------------------------------------
def test_user_directory_is_forbidden_to_regular_users(auth, user):
    assert auth(user).get("/api/admin/users").status_code == 403


def test_user_directory_is_allowed_to_the_global_admin(auth, admin_user, user):
    response = auth(admin_user).get("/api/admin/users")
    assert response.status_code == 200
    usernames = [row["username"] for row in response.data]
    assert admin_user.username in usernames


# --- teams / players ------------------------------------------------------
def test_players_can_be_filtered_by_competition(auth, user):
    lec_team = ProTeamFactory(competition=Competition.LEC)
    lck_team = ProTeamFactory(competition=Competition.LCK)
    ProPlayerFactory(team=lec_team, competition=Competition.LEC, nickname="EuPlayer")
    ProPlayerFactory(team=lck_team, competition=Competition.LCK, nickname="KrPlayer")

    client = auth(user)
    response = client.get("/api/players?competition=LCK")
    assert response.status_code == 200
    assert [row["nickname"] for row in response.data] == ["KrPlayer"]


def test_player_response_keeps_the_legacy_field_names(auth, user):
    player = ProPlayerFactory(nome_reale="Rasmus Winther", image_url="/img/caps.jpg")
    response = auth(user).get(f"/api/players/{player.id}")
    assert response.status_code == 200
    assert set(response.data) >= {"id", "nickname", "nomeReale", "nazionalita", "ruolo",
                                  "quotazione", "teamId", "teamNome", "imageUrl"}


def test_regular_users_cannot_create_players(auth, user):
    team = ProTeamFactory()
    response = auth(user).post("/api/players", {
        "nickname": "Abusivo", "ruolo": "MID", "quotazione": 10, "teamId": team.id,
    }, format="json")
    assert response.status_code == 403


# --- leghe ----------------------------------------------------------------
def test_league_creation_and_join_flow(auth, user):
    client = auth(user)
    created = client.post("/api/leagues", {"nome": "Lega Test", "creditiIniziali": 700},
                          format="json")
    assert created.status_code == 201
    assert created.data["creditiIniziali"] == 700
    assert created.data["maxRosterSize"] == 10
    assert created.data["competitionStarted"] is False

    joined = client.post("/api/fanta-teams/join",
                         {"codiceInvito": created.data["codiceInvito"],
                          "nomeSquadra": "I miei"}, format="json")
    assert joined.status_code == 201
    assert joined.data["creditiResidui"] == 700
    assert joined.data["rosa"] == []


def test_league_detail_is_forbidden_to_outsiders(auth, user):
    league = LeagueFactory()
    assert auth(user).get(f"/api/leagues/{league.id}").status_code == 403


def test_fanta_team_response_exposes_the_roster(auth, user):
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league, owner=user)
    player = ProPlayerFactory(nickname="Caps")
    RosterEntryFactory(fanta_team=team, player=player, crediti_spesi=42)

    response = auth(user).get(f"/api/fanta-teams/{team.id}")
    assert response.status_code == 200
    entry = response.data["rosa"][0]
    assert entry["lecPlayerNickname"] == "Caps"
    assert entry["creditiSpesi"] == 42
    assert entry["ruolo"] == player.ruolo


# --- formazioni -----------------------------------------------------------
def test_lineup_window_endpoint_reports_editability(auth, user):
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league, owner=user)
    response = auth(user).get(f"/api/fanta-teams/{team.id}/formazioni/window")
    assert response.status_code == 200
    assert set(response.data) == {"editable", "nextEffectiveAt", "reason"}


def test_fixed_roster_leagues_report_a_non_editable_lineup(auth, user):
    league = LeagueFactory(participant_count=8)
    team = FantaTeamFactory(league=league, owner=user)
    response = auth(user).get(f"/api/fanta-teams/{team.id}/formazioni/window")
    assert response.data["editable"] is False


def test_lineup_endpoint_falls_back_to_the_roster_in_fixed_leagues(auth, user):
    league = LeagueFactory(participant_count=8)
    team = FantaTeamFactory(league=league, owner=user)
    pro_team = ProTeamFactory()
    for role in ROLE_ORDER:
        RosterEntryFactory(fanta_team=team,
                           player=ProPlayerFactory(team=pro_team, ruolo=role.value))
    response = auth(user).get(f"/api/fanta-teams/{team.id}/formazioni/lineup")
    assert response.status_code == 200
    assert len(response.data["players"]) == 5
    assert response.data["editable"] is False


def test_another_user_cannot_read_a_team_lineup(auth, user):
    team = FantaTeamFactory(league=LeagueFactory(participant_count=2))
    response = auth(user).get(f"/api/fanta-teams/{team.id}/formazioni/lineup")
    assert response.status_code == 400


# --- scoring --------------------------------------------------------------
def test_cumulative_performances_require_authentication(api):
    assert api.get("/api/lec/cumulative-performances").status_code == 401


def test_cumulative_performances_include_the_attribution(auth, user):
    response = auth(user).get("/api/lec/cumulative-performances")
    assert response.status_code == 200
    assert "Leaguepedia" in response.data["attribution"]
    assert response.data["items"] == []


def test_league_ranking_is_scoped_to_league_members(auth, user):
    league = LeagueFactory()
    assert auth(user).get(f"/api/leagues/{league.id}/cumulative-ranking").status_code == 403


# --- ingest (admin) -------------------------------------------------------
def test_ingest_status_is_admin_only(auth, user, admin_user):
    assert auth(user).get("/api/admin/ingest/status").status_code == 403


def test_ingest_status_is_readable_by_the_admin(auth, admin_user):
    response = auth(admin_user).get("/api/admin/ingest/status")
    assert response.status_code == 200
    assert response.data == []


def test_matches_endpoint_never_calls_a_provider(auth, user):
    response = auth(user).get("/api/matches?competition=LEC")
    assert response.status_code == 200
    assert response.data["items"] == []
    assert "Leaguepedia" in response.data["attribution"]


# --- docs -----------------------------------------------------------------
def test_openapi_schema_is_served():
    from django.test import Client

    response = Client().get("/api/schema/")
    assert response.status_code == 200
