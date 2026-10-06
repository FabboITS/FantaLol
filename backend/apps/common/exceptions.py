"""Errori applicativi e formato uniforme ``ApiError`` (identico al backend Java)."""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, JsonResponse
from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class BusinessRuleException(Exception):
    """Violazione di una regola di business (crediti insufficienti, formazione non valida...)."""

    status_code = 422

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ResourceNotFoundException(Exception):
    """Risorsa richiesta inesistente."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AccessDeniedException(Exception):
    """L'utente autenticato non può accedere alla risorsa."""

    def __init__(self, message: str = "Non hai i permessi per eseguire questa operazione"):
        super().__init__(message)
        self.message = message


REASONS = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}


def api_error(status_code: int, message: str, path: str, details: list[str] | None = None) -> dict[str, Any]:
    return {
        "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
        "status": status_code,
        "error": REASONS.get(status_code, "Error"),
        "message": message,
        "path": path,
        "details": details or [],
    }


def _flatten_validation(detail: Any, prefix: str = "") -> list[str]:
    if isinstance(detail, dict):
        out: list[str] = []
        for key, value in detail.items():
            name = key if key != "non_field_errors" else ""
            out.extend(_flatten_validation(value, f"{prefix}{name}"))
        return out
    if isinstance(detail, list):
        out = []
        for item in detail:
            out.extend(_flatten_validation(item, prefix))
        return out
    text = str(detail)
    return [f"{_camel(prefix)}: {text}" if prefix else text]


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    request = context.get("request")
    path = request.path if request is not None else ""
    if isinstance(exc, BusinessRuleException):
        return Response(api_error(422, exc.message, path), status=422)
    if isinstance(exc, ResourceNotFoundException):
        return Response(api_error(404, exc.message, path), status=404)
    if isinstance(exc, AccessDeniedException | DjangoPermissionDenied):
        message = getattr(exc, "message", None) or "Non hai i permessi per eseguire questa operazione"
        return Response(api_error(403, message, path), status=403)
    if isinstance(exc, Http404):
        return Response(api_error(404, "Risorsa non trovata", path), status=404)
    if isinstance(exc, exceptions.ValidationError):
        details = _flatten_validation(exc.detail)
        return Response(
            api_error(400, "Errore di validazione dei dati", path, details),
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, exceptions.ParseError):
        return Response(api_error(400, "Richiesta non valida", path), status=400)
    if isinstance(exc, exceptions.AuthenticationFailed | exceptions.NotAuthenticated):
        response = Response(api_error(401, "Unauthorized", path), status=401)
        response["WWW-Authenticate"] = 'Bearer realm="api"'
        return response
    if isinstance(exc, exceptions.PermissionDenied):
        return Response(api_error(403, "Non hai i permessi per eseguire questa operazione", path), status=403)
    if isinstance(exc, exceptions.MethodNotAllowed):
        return Response(api_error(405, "Metodo non consentito", path), status=405)
    if isinstance(exc, exceptions.APIException):
        return Response(api_error(exc.status_code, str(exc.detail), path), status=exc.status_code)
    if isinstance(exc, ValueError):
        return Response(api_error(400, str(exc), path), status=400)
    logger.exception("Errore imprevisto su %s", path)
    return Response(api_error(500, "Si è verificato un errore imprevisto", path), status=500)


def json_404(request, exception=None):  # pragma: no cover - collegato a handler404
    return JsonResponse(api_error(404, "Risorsa non trovata", request.path), status=404)


def json_500(request):  # pragma: no cover - collegato a handler500
    return JsonResponse(api_error(500, "Si è verificato un errore imprevisto", request.path), status=500)
