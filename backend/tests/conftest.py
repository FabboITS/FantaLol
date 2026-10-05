import pytest
from rest_framework.test import APIClient

from apps.users.services import login

from .factories import AdminFactory, UserFactory


@pytest.fixture
def api():
    return APIClient()


def auth_client(user) -> APIClient:
    client = APIClient()
    token = login(user.username, "password123")["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def admin(db):
    return AdminFactory()


@pytest.fixture
def user_client(user):
    return auth_client(user)


@pytest.fixture
def admin_client(admin):
    return auth_client(admin)
