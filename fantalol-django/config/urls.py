"""Routing globale delle API FantaLoL.

I path replicano quelli dell'applicazione Spring Boot per non rompere il
frontend esistente; le rotte Worlds sono additive sotto `/api/worlds/`.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
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

# --- Frontend locale ------------------------------------------------------
# Solo in sviluppo: serve il frontend provvisorio sulla stessa origine delle
# API, così basta un processo e non serve configurare CORS. Le rotte stanno in
# fondo perché `/api/` ha sempre la precedenza.
if settings.SERVE_LOCAL_FRONTEND and settings.LOCAL_FRONTEND_DIR.exists():
    frontend = {"document_root": str(settings.LOCAL_FRONTEND_DIR)}
    assets = {"document_root": str(settings.LOCAL_ASSETS_DIR)}
    urlpatterns += [
        path("", serve, {**frontend, "path": "index.html"}, name="local-frontend-home"),
        re_path(r"^(?P<path>(?:css|js)/.*)$", serve, frontend),
        re_path(r"^(?P<path>lega\.html)$", serve, frontend),
        # Immagini e loghi vengono dal frontend definitivo.
        re_path(r"^(?P<path>(?:Player_immage|assets)/.*)$", serve, assets),
        re_path(r"^(?P<path>favicon\.svg)$", serve, assets),
    ]
