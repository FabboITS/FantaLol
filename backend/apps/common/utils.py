"""Utility condivise: ruoli dei player, parsing dei parametri, orologio iniettabile."""

from __future__ import annotations

from datetime import UTC, datetime

from django.db import models
from django.utils import timezone
from rest_framework.exceptions import ValidationError


class PlayerRole(models.TextChoices):
    TOP = "TOP", "Top"
    JUNGLE = "JUNGLE", "Jungle"
    MID = "MID", "Mid"
    ADC = "ADC", "ADC"
    SUPPORT = "SUPPORT", "Support"


ROLE_ORDER = [PlayerRole.TOP, PlayerRole.JUNGLE, PlayerRole.MID, PlayerRole.ADC, PlayerRole.SUPPORT]
ROLE_VALUES = [r.value for r in ROLE_ORDER]


def now() -> datetime:
    """Orologio dell'applicazione (sostituibile nei test con freezegun)."""
    return timezone.now()


def role_index(role: str) -> int:
    return ROLE_VALUES.index(role) if role in ROLE_VALUES else len(ROLE_VALUES)


def int_param(
    value,
    name: str,
    *,
    required: bool = False,
    minimum: int | None = None,
    maximum: int | None = None,
    default: int | None = None,
) -> int | None:
    if value in (None, ""):
        if required:
            raise ValidationError({name: "Parametro obbligatorio"})
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Deve essere un numero intero"})
    if minimum is not None and number < minimum or maximum is not None and number > maximum:
        raise ValidationError({name: f"Deve essere compreso tra {minimum} e {maximum}"})
    return number


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
