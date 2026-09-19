from django.urls import path

from .views import CumulativePerformancesView

urlpatterns = [
    # Path storico mantenuto per compatibilità con il frontend esistente.
    path("lec/cumulative-performances", CumulativePerformancesView.as_view(),
         name="cumulative-performances-legacy"),
    path("cumulative-performances", CumulativePerformancesView.as_view(),
         name="cumulative-performances"),
]
