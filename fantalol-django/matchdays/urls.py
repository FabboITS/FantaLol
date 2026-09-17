from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FormationConfirmAllView,
    FormationConfirmView,
    FormationDetailView,
    FormationHistoryView,
    LineupView,
    LineupWindowView,
    MatchdayViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("matchdays", MatchdayViewSet, basename="matchdays")

urlpatterns = router.urls + [
    path("fanta-teams/<int:fanta_team_id>/formazioni", FormationHistoryView.as_view(),
         name="formation-history"),
    path("fanta-teams/<int:fanta_team_id>/formazioni/window", LineupWindowView.as_view(),
         name="lineup-window"),
    path("fanta-teams/<int:fanta_team_id>/formazioni/lineup", LineupView.as_view(),
         name="lineup"),
    path("fanta-teams/<int:fanta_team_id>/formazioni/<int:matchday_id>",
         FormationDetailView.as_view(), name="formation-detail"),
    path("fanta-teams/<int:fanta_team_id>/formazioni/<int:matchday_id>/confirm",
         FormationConfirmView.as_view(), name="formation-confirm"),
    path("admin/leagues/<int:league_id>/matchdays/<int:matchday_id>/formations/confirm-all",
         FormationConfirmAllView.as_view(), name="formation-confirm-all"),
]
