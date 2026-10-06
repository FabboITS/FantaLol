"""Registrazione, login e profilo (porting di ``UserService``)."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework_simplejwt.tokens import AccessToken

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException

from .models import Role, User, UserProfile


class InvalidCredentials(Exception):
    pass


def user_response(user: User) -> dict:
    profile = getattr(user, "profile", None) if hasattr(user, "profile") else None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "nome_visualizzato": profile.nome_visualizzato if profile else None,
    }


@transaction.atomic
def register(username: str, email: str, password: str) -> User:
    if User.objects.filter(username=username).exists():
        raise BusinessRuleException(f"Username già in uso: {username}")
    if User.objects.filter(email=email).exists():
        raise BusinessRuleException(f"Email già registrata: {email}")
    return User.objects.create_user(username=username, email=email, password=password, role=Role.USER)


def login(username: str, password: str) -> dict:
    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        raise InvalidCredentials()
    token = AccessToken.for_user(user)
    token["authorities"] = [f"ROLE_{user.role}"]
    token["sub"] = user.username
    return {"token": str(token), "token_type": "Bearer", "username": user.username, "role": user.role}


def find_by_username(username: str) -> User:
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        raise ResourceNotFoundException(f"Utente non trovato: {username}")


def regular_user_directory() -> list[dict]:
    return [
        {"username": u.username, "email": u.email}
        for u in User.objects.filter(role=Role.USER).order_by("username")
    ]


@transaction.atomic
def update_profile(user: User, data: dict) -> User:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.nome_visualizzato = data.get("nome_visualizzato")
    profile.bio = data.get("bio")
    profile.avatar_url = data.get("avatar_url")
    profile.summoner_name = data.get("summoner_name")
    profile.save()
    user.refresh_from_db()
    return user
