import pytest
from rest_framework.test import APIClient

from .factories import AdminFactory, UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory(password="password123")


@pytest.fixture
def admin_user():
    return AdminFactory(password="password123")


@pytest.fixture
def auth(api):
    """Autentica il client con un utente, via JWT."""
    def _auth(account):
        response = api.post("/api/auth/login",
                            {"username": account.username, "password": "password123"},
                            format="json")
        assert response.status_code == 200, response.data
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
        return api
    return _auth
