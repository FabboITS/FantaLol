from django.urls import path

from .views import (
    LoginView,
    MeProfileView,
    MeView,
    RefreshView,
    RegisterView,
    UserDirectoryView,
)

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("users/me", MeView.as_view(), name="users-me"),
    path("users/me/profile", MeProfileView.as_view(), name="users-me-profile"),
    path("admin/users", UserDirectoryView.as_view(), name="admin-users"),
]
