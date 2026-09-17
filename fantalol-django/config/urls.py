"""Routing globale delle API FantaLoL.

I path replicano quelli dell'applicazione Spring Boot per non rompere il
frontend esistente; le rotte Worlds sono additive sotto `/api/worlds/`.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("teams.urls")),
    path("api/", include("leagues.urls")),
    path("api/", include("matchdays.urls")),
    path("api/", include("scoring.urls")),
    path("api/", include("ingest.urls")),
    path("api/worlds/", include("worlds.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
