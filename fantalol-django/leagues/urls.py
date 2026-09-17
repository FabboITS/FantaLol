from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AuctionActiveView, AuctionBidView, FantaTeamViewSet, LeagueViewSet

router = DefaultRouter(trailing_slash=False)
router.register("leagues", LeagueViewSet, basename="leagues")
router.register("fanta-teams", FantaTeamViewSet, basename="fanta-teams")

urlpatterns = router.urls + [
    path("auctions/active", AuctionActiveView.as_view(), name="auction-active"),
    path("auctions", AuctionActiveView.as_view(), name="auction-start"),
    path("auctions/<int:pk>/bids", AuctionBidView.as_view(), name="auction-bid"),
]
