"""Permessi riusabili (equivalenti alle `@PreAuthorize` di Spring)."""
from rest_framework.permissions import BasePermission


class IsGlobalAdmin(BasePermission):
    """Solo l'ADMIN globale seedato all'avvio."""

    message = "Operazione riservata all'amministratore"

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_global_admin)


class IsAuthenticatedReadOnlyOrAdmin(BasePermission):
    """Lettura per ogni utente autenticato, scrittura solo per l'ADMIN."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return user.is_global_admin
