"""Porting di AuthIntegrationTest, AdminUserDirectoryIntegrationTest e UserServiceTest."""

import pytest
from django.core.management import call_command

from apps.common.exceptions import BusinessRuleException
from apps.users import services
from apps.users.models import Role, User

from .conftest import auth_client
from .factories import AdminFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_registrazione_e_login_restituiscono_un_token_valido(api):
    response = api.post(
        "/api/auth/register",
        {"username": "integrazione", "email": "int@test.local", "password": "segreta1"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["username"] == "integrazione"
    assert response.json()["role"] == "USER"
    login = api.post("/api/auth/login", {"username": "integrazione", "password": "segreta1"}, format="json")
    assert login.status_code == 200
    body = login.json()
    assert body["token"]
    assert body["tokenType"] == "Bearer"
    assert body["role"] == "USER"
    assert body["username"] == "integrazione"


def test_non_permette_la_registrazione_con_dati_non_validi(api):
    response = api.post(
        "/api/auth/register", {"username": "ab", "email": "non-valida", "password": "1"}, format="json"
    )
    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Errore di validazione dei dati"
    assert set(body) == {"timestamp", "status", "error", "message", "path", "details"}
    assert any(d.startswith("username:") for d in body["details"])
    assert any(d.startswith("email:") for d in body["details"])


def test_login_con_credenziali_errate_restituisce_401(api):
    UserFactory(username="mago")
    response = api.post("/api/auth/login", {"username": "mago", "password": "sbagliata"}, format="json")
    assert response.status_code == 401
    assert response.json()["message"] == "Credenziali non valide"


def test_registrazione_duplicata_e_una_violazione_di_regola(api):
    UserFactory(username="mago", email="mago@fantalol.it")
    response = api.post(
        "/api/auth/register",
        {"username": "mago", "email": "altro@fantalol.it", "password": "segreta1"},
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["message"] == "Username già in uso: mago"
    response = api.post(
        "/api/auth/register",
        {"username": "nuovo", "email": "mago@fantalol.it", "password": "segreta1"},
        format="json",
    )
    assert response.json()["message"] == "Email già registrata: mago@fantalol.it"


def test_endpoint_di_consultazione_pubblica_accessibili_senza_token(api):
    assert api.get("/api/teams").status_code == 200
    assert api.get("/api/players").status_code == 200
    assert api.get("/api/matchdays").status_code == 200
    assert api.get("/api/competitions").status_code == 200
    assert api.get("/api/health").status_code == 200


def test_endpoint_protetti_richiedono_token(api):
    response = api.get("/api/users/me")
    assert response.status_code == 401
    assert response.json()["status"] == 401
    api.credentials(HTTP_AUTHORIZATION="Bearer token-non-valido")
    assert api.get("/api/users/me").status_code == 401


def test_utente_autenticato_accede_al_proprio_profilo_e_lo_aggiorna(user, user_client):
    response = user_client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json()["username"] == user.username
    assert response.json()["nomeVisualizzato"] is None
    updated = user_client.put(
        "/api/users/me/profile", {"nomeVisualizzato": "Il Mago", "bio": "ciao"}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["nomeVisualizzato"] == "Il Mago"


def test_token_di_un_utente_eliminato_restituisce_unauthorized(user):
    client = auth_client(user)
    user.delete()
    assert client.get("/api/users/me").status_code == 401


def test_rotte_di_sincronizzazione_e_correzione_richiedono_admin_globale(user_client, admin_client):
    assert user_client.get("/api/admin/lec/synchronization").status_code == 403
    assert user_client.post("/api/admin/lec/synchronize").status_code == 403
    assert user_client.put("/api/admin/lec/games/GAME-1/players/1", {}, format="json").status_code == 403
    assert user_client.delete("/api/admin/lec/games/GAME-1/players/1/override").status_code == 403
    assert admin_client.get("/api/admin/lec/synchronization").status_code == 200


def test_admin_riceve_directory_ordinata_solo_username_ed_email(api):
    UserFactory(username="zeta", email="zeta@test.local")
    UserFactory(username="alpha", email="alpha@test.local")
    admin = AdminFactory(username="admin-test")
    response = auth_client(admin).get("/api/users")
    assert response.status_code == 200
    body = response.json()
    assert [u["username"] for u in body] == ["alpha", "zeta"]
    assert body[0] == {"username": "alpha", "email": "alpha@test.local"}
    assert "admin-test" not in [u["username"] for u in body]


def test_utente_normale_e_anonimo_non_leggono_la_directory(api, user_client):
    assert user_client.get("/api/users").status_code == 403
    assert api.get("/api/users").status_code == 401


def test_service_registra_correttamente_un_nuovo_utente():
    user = services.register("mago", "mago@fantalol.it", "segreta1")
    response = services.user_response(user)
    assert response["username"] == "mago"
    assert response["email"] == "mago@fantalol.it"
    assert response["role"] == "USER"
    assert user.check_password("segreta1")
    with pytest.raises(BusinessRuleException):
        services.register("mago", "x@fantalol.it", "segreta1")


def test_ensure_admin_crea_admin_da_variabili_ambiente(settings):
    settings.ADMIN_USERNAME, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD = "boss", "boss@x.it", "pwd-sicura"
    call_command("ensure_admin")
    call_command("ensure_admin")
    boss = User.objects.get(username="boss")
    assert boss.role == Role.ADMIN and boss.is_staff and boss.check_password("pwd-sicura")


def test_ensure_admin_senza_variabili_non_crea_nulla(settings, capsys):
    settings.ADMIN_USERNAME = None
    call_command("ensure_admin")
    assert not User.objects.filter(role=Role.ADMIN).exists()
    assert "nessun admin creato" in capsys.readouterr().err


def test_hash_bcrypt_del_backend_java_sono_accettati():
    import bcrypt

    legacy = bcrypt.hashpw(b"vecchia-password", bcrypt.gensalt(rounds=4)).decode().replace("$2b$", "$2a$", 1)
    user = UserFactory(username="legacy")
    User.objects.filter(pk=user.pk).update(password=f"bcrypt${legacy}")
    assert services.login("legacy", "vecchia-password")["username"] == "legacy"
