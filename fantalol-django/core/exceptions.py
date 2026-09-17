"""Gestione errori equivalente a `common/GlobalExceptionHandler` (Spring).

Il payload di errore mantiene la stessa forma del vecchio `ApiError` così che
il frontend attuale continui a leggere `message` / `status` / `timestamp`.
"""
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessRuleError(Exception):
    """Violazione di una regola di gioco: mappata su HTTP 400 (come in Spring)."""

    status_code = status.HTTP_400_BAD_REQUEST


class ResourceNotFound(Exception):
    """Entità inesistente: mappata su HTTP 404."""

    status_code = status.HTTP_404_NOT_FOUND


class AccessDenied(Exception):
    """Accesso negato a una risorsa altrui: mappata su HTTP 403."""

    status_code = status.HTTP_403_FORBIDDEN


def api_error(message: str, http_status: int, errors=None) -> Response:
    body = {
        "timestamp": timezone.now().isoformat(),
        "status": http_status,
        "message": message,
    }
    if errors:
        body["errors"] = errors
    return Response(body, status=http_status)


def _flatten(detail) -> str:
    if isinstance(detail, dict):
        parts = []
        for field, value in detail.items():
            parts.append(f"{field}: {_flatten(value)}")
        return "; ".join(parts)
    if isinstance(detail, list):
        return "; ".join(_flatten(item) for item in detail)
    return str(detail)


def api_exception_handler(exc, context):
    if isinstance(exc, BusinessRuleError):
        return api_error(str(exc), BusinessRuleError.status_code)
    if isinstance(exc, (ResourceNotFound, ObjectDoesNotExist, Http404)):
        message = str(exc) or "Risorsa non trovata"
        return api_error(message, ResourceNotFound.status_code)
    if isinstance(exc, (AccessDenied, DjangoPermissionDenied)):
        return api_error(str(exc) or "Accesso negato", AccessDenied.status_code)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    message = detail.get("detail") if isinstance(detail, dict) and "detail" in detail else _flatten(detail)
    errors = detail if isinstance(detail, dict) and "detail" not in detail else None
    return api_error(str(message), response.status_code, errors)
