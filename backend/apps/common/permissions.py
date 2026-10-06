"""Permessi DRF che riproducono la matrice di ``SecurityConfig`` del backend Java."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_global_admin(user) -> bool:
    return bool(user and user.is_authenticated and getattr(user, "role", None) == "ADMIN")


class IsGlobalAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_global_admin(request.user)


class PublicReadAdminWrite(BasePermission):
    """GET pubblici, scritture riservate al ruolo ADMIN (team e player)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_global_admin(request.user)


class PublicReadAuthenticatedWrite(BasePermission):
    """GET pubblici, scritture per utenti autenticati (giornate: il service verifica l'admin di lega)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
