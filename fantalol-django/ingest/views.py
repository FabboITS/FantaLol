"""API di lettura dei dati pro e amministrazione dell'ingest.

Il frontend legge **solo** da qui: nessuna chiamata diretta ai provider esterni.
"""
from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import ResourceNotFound
from core.permissions import IsGlobalAdmin
from scoring.services import recompute_scores_for_game

from .models import Game, GamePlayerStat, Match, SyncState
from .serializers import (
    GameSerializer,
    MatchDetailSerializer,
    MatchSerializer,
    PlayerStatCorrectionSerializer,
    SyncStateSerializer,
)

ATTRIBUTION = settings.LEAGUEPEDIA["ATTRIBUTION"]


@extend_schema(parameters=[
    OpenApiParameter("competition", str, description="LEC/LPL/LCK"),
    OpenApiParameter("status", str, description="not_started/running/finished"),
])
class MatchListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Match.objects.all()
        competition = request.query_params.get("competition") or request.query_params.get("league")
        if competition:
            queryset = queryset.filter(league_code=competition.upper())
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        queryset = queryset.order_by("-begin_at")[:200]
        return Response({
            "items": MatchSerializer(queryset, many=True).data,
            "attribution": ATTRIBUTION,
        })


class MatchDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pandascore_id=None):
        match = (Match.objects.prefetch_related("games__player_stats__player")
                 .filter(pandascore_id=pandascore_id).first())
        if match is None:
            raise ResourceNotFound(f"Serie non trovata con id: {pandascore_id}")
        return Response({
            "match": MatchDetailSerializer(match).data,
            "attribution": ATTRIBUTION,
        })


class GameDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, external_game_id=None):
        game = (Game.objects.prefetch_related("player_stats__player")
                .filter(external_game_id=external_game_id).first())
        if game is None:
            raise ResourceNotFound(f"Game non trovato: {external_game_id}")
        return Response({"game": GameSerializer(game).data, "attribution": ATTRIBUTION})


class SyncStatusView(APIView):
    """`/api/admin/ingest/status`: stato dei due provider."""

    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        return Response(SyncStateSerializer(SyncState.objects.all(), many=True).data)


class TriggerSyncView(APIView):
    """`/api/admin/ingest/sync`: forza un ciclo (sostituisce il sync manuale LEC)."""

    permission_classes = [IsGlobalAdmin]

    def post(self, request, provider=None):
        from .services import enrich_leaguepedia, sync_pandascore

        if provider == "pandascore":
            report = sync_pandascore()
        elif provider == "leaguepedia":
            report = enrich_leaguepedia()
        else:
            raise ResourceNotFound(f"Provider sconosciuto: {provider}")
        return Response({
            "provider": provider,
            "inserted": report.inserted,
            "updated": report.updated,
            "skipped": report.skipped,
            "failed": report.failed,
            "errors": report.errors[:20],
        })


class PlayerStatCorrectionView(APIView):
    """Correzione manuale di un box score (equivalente di `PlayerGameCorrectionService`)."""

    permission_classes = [IsGlobalAdmin]

    def put(self, request, external_game_id=None, player_id=None):
        stat = (GamePlayerStat.objects.select_related("game", "player")
                .filter(game__external_game_id=external_game_id, player_id=player_id).first())
        if stat is None:
            raise ResourceNotFound("Statistica non trovata per il game e il player indicati")
        serializer = PlayerStatCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        mapping = {
            "kills": "corrected_kills",
            "deaths": "corrected_deaths",
            "assists": "corrected_assists",
            "cs": "corrected_cs",
            "visionScore": "corrected_vision_score",
            "win": "corrected_win",
            "participated": "corrected_participated",
        }
        for key, attr in mapping.items():
            if key in data:
                setattr(stat, attr, data[key])
        stat.overridden = True
        stat.override_actor = request.user.username
        stat.overridden_at = timezone.now()
        stat.recompute_fantasy_score()
        stat.save()
        return Response({"updated": True, "fantasyScore": stat.fantasy_score})

    def delete(self, request, external_game_id=None, player_id=None):
        """Rimuove l'override e ripristina i valori grezzi del provider."""
        stat = (GamePlayerStat.objects.select_related("game", "player")
                .filter(game__external_game_id=external_game_id, player_id=player_id).first())
        if stat is None:
            raise ResourceNotFound("Statistica non trovata per il game e il player indicati")
        stat.corrected_kills = None
        stat.corrected_deaths = None
        stat.corrected_assists = None
        stat.corrected_cs = None
        stat.corrected_vision_score = None
        stat.corrected_win = None
        stat.corrected_participated = None
        stat.overridden = False
        stat.override_actor = None
        stat.overridden_at = None
        stat.recompute_fantasy_score()
        stat.save()
        recompute_scores_for_game(stat.game)
        return Response({"restored": True, "fantasyScore": stat.fantasy_score})
