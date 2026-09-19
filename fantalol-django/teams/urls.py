from rest_framework.routers import DefaultRouter

from .views import ProPlayerViewSet, ProTeamViewSet

router = DefaultRouter(trailing_slash=False)
router.register("teams", ProTeamViewSet, basename="teams")
router.register("players", ProPlayerViewSet, basename="players")

urlpatterns = router.urls
