"""Endpoint dei punteggi cumulativi (compatibili con il frontend attuale)."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


@extend_schema(parameters=[OpenApiParameter("competition", str, description="LEC/LPL/LCK")])
class CumulativePerformancesView(APIView):
    """Storico `/api/lec/cumulative-performances`, ora multi-competitivo."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        competition = request.query_params.get("competition")
        return Response(services.player_scores_response(competition))
