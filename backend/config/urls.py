from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health
from apps.esports import views as esports
from apps.leagues import views as leagues
from apps.matchdays import views as matchdays
from apps.users import views as users
from apps.worlds import views as worlds

handler404 = "apps.common.exceptions.json_404"
handler500 = "apps.common.exceptions.json_500"


def media(request, path):
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response["Cache-Control"] = "public, max-age=86400"
    return response


def competition_routes(prefix: str, **kwargs):
    """Rotte dati per competizione; ``/api/lec/*`` resta come alias di ``/api/competitions/lec/*``."""
    return [
        path(f"{prefix}/standings", esports.standings, kwargs),
        path(f"{prefix}/performances", esports.performances, kwargs),
        path(f"{prefix}/cumulative-performances", esports.cumulative_performances, kwargs),
        path(f"{prefix}/matches", esports.competition_matches, kwargs),
        path(f"{prefix}/matches/<str:match_id>/games/<str:game_id>", esports.competition_game, kwargs),
    ]


urlpatterns = [
    path("api/health", health),
    # Auth e utenti
    path("api/auth/register", users.register),
    path("api/auth/login", users.login),
    path("api/users", users.directory),
    path("api/users/me", users.me),
    path("api/users/me/profile", users.update_profile),
    # Competizioni e dati reali
    path("api/competitions", esports.competitions),
    path("api/competitions/<str:code>/editions", esports.competition_editions),
    *competition_routes("api/competitions/<str:code>"),
    *competition_routes("api/lec", code="lec"),
    path("api/teams", esports.teams),
    path("api/teams/<int:team_id>", esports.team_detail),
    path("api/players", esports.players),
    path("api/players/<int:player_id>", esports.player_detail),
    path("api/esports/matches", esports.esports_matches),
    path("api/esports/matches/<int:match_id>/games", esports.esports_match_games),
    # Leghe, FantaTeam, aste
    path("api/leagues", leagues.leagues),
    path("api/leagues/<int:league_id>", leagues.league_detail),
    path("api/leagues/<int:league_id>/auction/<str:action>", leagues.auction_phase),
    path("api/leagues/<int:league_id>/rosters/complete-randomly", leagues.complete_randomly),
    path("api/leagues/<int:league_id>/cumulative-ranking", leagues.cumulative_ranking),
    path("api/fanta-teams/join", leagues.join),
    path("api/fanta-teams/me", leagues.my_teams),
    path("api/fanta-teams/<int:team_id>", leagues.team_detail),
    path("api/fanta-teams/by-league/<int:league_id>", leagues.teams_by_league),
    path("api/fanta-teams/<int:team_id>/rosa/gratis", leagues.free_player),
    path("api/fanta-teams/<int:team_id>/rosa/<int:entry_id>", leagues.release_player),
    path("api/fanta-teams/<int:team_id>/cumulative-score", leagues.cumulative_score),
    path("api/auctions/active", leagues.active_auction),
    path("api/auctions", leagues.start_auction),
    path("api/auctions/<int:auction_id>/bids", leagues.bid),
    # Giornate e formazioni
    path("api/matchdays", matchdays.matchdays),
    path("api/matchdays/<int:matchday_id>", matchdays.matchday_detail),
    path("api/matchdays/<int:matchday_id>/stats", matchdays.matchday_stats),
    path("api/matchdays/<int:matchday_id>/chiudi", matchdays.close_matchday),
    path("api/matchdays/<int:matchday_id>/waiting-for-postponed", matchdays.waiting_for_postponed),
    path("api/fanta-teams/<int:team_id>/formazioni", matchdays.formations_root),
    path("api/fanta-teams/<int:team_id>/formazioni/window", matchdays.formation_window),
    path("api/fanta-teams/<int:team_id>/formazioni/lineup", matchdays.formation_lineup),
    path("api/fanta-teams/<int:team_id>/formazioni/<int:matchday_id>", matchdays.formation_by_matchday),
    path("api/fanta-teams/<int:team_id>/formazioni/<int:matchday_id>/confirm", matchdays.confirm_formation),
    path(
        "api/admin/leagues/<int:league_id>/matchdays/<int:matchday_id>/formations/confirm-all",
        matchdays.confirm_all,
    ),
    # WORLDS
    path("api/worlds/leagues/<int:league_id>/market", worlds.market),
    path("api/worlds/fanta-teams/<int:team_id>/transfers", worlds.transfers),
    path("api/admin/worlds/editions/<int:edition_id>/publish-listone", worlds.publish_listone),
    path("api/admin/worlds/players/<int:player_id>/price", worlds.set_price),
    # Admin dati reali (con alias /api/admin/lec/...)
    path("api/admin/competitions/<str:code>/synchronize", esports.synchronize),
    path("api/admin/competitions/<str:code>/synchronization", esports.synchronization),
    path("api/admin/lec/synchronize", esports.synchronize),
    path("api/admin/lec/synchronization", esports.synchronization),
    path("api/admin/games/<str:game_id>/players/<int:player_id>", esports.correct_player_game),
    path("api/admin/games/<str:game_id>/players/<int:player_id>/override", esports.restore_player_game),
    path("api/admin/lec/games/<str:game_id>/players/<int:player_id>", esports.correct_player_game),
    path("api/admin/lec/games/<str:game_id>/players/<int:player_id>/override", esports.restore_player_game),
    path("api/admin/esports/unmatched-stats", esports.unmatched_stats),
    path("api/admin/esports/aliases/<str:kind>", esports.create_alias),
    path("api/admin/esports/matches/<int:match_id>/games", esports.create_manual_game),
    # OpenAPI
    path("v3/api-docs", SpectacularAPIView.as_view(), name="schema"),
    path("swagger-ui.html", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("django-admin/", admin.site.urls),
    re_path(r"^media/(?P<path>.+)$", media),
]
