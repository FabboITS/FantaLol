from django.urls import path

from .views import (
    GameDetailView,
    MatchDetailView,
    MatchListView,
    PlayerStatCorrectionView,
    SyncStatusView,
    TriggerSyncView,
)

urlpatterns = [
    path("matches", MatchListView.as_view(), name="matches"),
    path("matches/<int:pandascore_id>", MatchDetailView.as_view(), name="match-detail"),
    path("games/<str:external_game_id>", GameDetailView.as_view(), name="game-detail"),
    path("admin/ingest/status", SyncStatusView.as_view(), name="ingest-status"),
    path("admin/ingest/<str:provider>/sync", TriggerSyncView.as_view(), name="ingest-sync"),
    path("admin/ingest/games/<str:external_game_id>/players/<int:player_id>",
         PlayerStatCorrectionView.as_view(), name="ingest-stat-correction"),
]
