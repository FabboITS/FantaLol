"""`/api/teams` e `/api/players`, con filtro `?competition=LEC|LPL|LCK`."""
from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets

from core.permissions import IsAuthenticatedReadOnlyOrAdmin

from .models import ProPlayer, ProTeam
from .serializers import ProPlayerSerializer, ProTeamSerializer


@extend_schema(parameters=[
    OpenApiParameter("competition", str, description="Filtra per competitivo pro (LEC/LPL/LCK/...)"),
    OpenApiParameter("worldsEligible", bool, description="Solo squadre con almeno un player qualificato a Worlds"),
])
class ProTeamViewSet(viewsets.ModelViewSet):
    serializer_class = ProTeamSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = ProTeam.objects.prefetch_related("giocatori").all()
        competition = self.request.query_params.get("competition")
        if competition:
            queryset = queryset.filter(competition=competition.upper())
        if self.request.query_params.get("worldsEligible") in {"1", "true", "True"}:
            queryset = queryset.filter(giocatori__is_worlds_eligible=True).distinct()
        return queryset


@extend_schema(parameters=[
    OpenApiParameter("competition", str, description="Filtra per competitivo pro (LEC/LPL/LCK/...)"),
    OpenApiParameter("ruolo", str, description="Filtra per ruolo (TOP/JUNGLE/MID/ADC/SUPPORT)"),
    OpenApiParameter("worldsEligible", bool, description="Solo player qualificati a Worlds"),
])
class ProPlayerViewSet(viewsets.ModelViewSet):
    serializer_class = ProPlayerSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = ProPlayer.objects.select_related("team").all()
        params = self.request.query_params
        if params.get("competition"):
            queryset = queryset.filter(competition=params["competition"].upper())
        if params.get("ruolo"):
            queryset = queryset.filter(ruolo=params["ruolo"].upper())
        if params.get("worldsEligible") in {"1", "true", "True"}:
            queryset = queryset.filter(is_worlds_eligible=True)
        return queryset
