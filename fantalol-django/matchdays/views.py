"""Endpoint `/api/matchdays` e `/api/fanta-teams/{id}/formazioni`."""
from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.exceptions import ResourceNotFound
from leagues import services as league_services
from teams.models import ProPlayer

from . import services
from .models import Formation, Matchday, PlayerStat
from .serializers import (
    FormationRequestSerializer,
    LineupRequestSerializer,
    MatchdayRequestSerializer,
    MatchdayResponseSerializer,
    PlayerStatRequestSerializer,
    PlayerStatResponseSerializer,
)


class MatchdayViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        queryset = Matchday.objects.select_related("league").all()
        league_id = request.query_params.get("leagueId")
        if league_id:
            league = league_services.get_league_or_404(league_id)
            league_services.assert_can_view_league(request.user, league)
            queryset = queryset.filter(league=league)
        elif not request.user.is_global_admin:
            queryset = queryset.filter(league__in=league_services.visible_leagues(request.user))
        return Response(MatchdayResponseSerializer(queryset, many=True).data)

    def retrieve(self, request, pk=None):
        matchday = services.get_matchday_or_404(pk)
        league_services.assert_can_view_league(request.user, matchday.league)
        return Response(MatchdayResponseSerializer(matchday).data)

    def create(self, request):
        serializer = MatchdayRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        matchday = services.create_matchday(
            request.user, data["leagueId"], data["numero"],
            data.get("descrizione"), data.get("data"))
        return Response(MatchdayResponseSerializer(matchday).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="stats")
    def stats(self, request, pk=None):
        matchday = services.get_matchday_or_404(pk)
        if request.method == "GET":
            league_services.assert_can_view_league(request.user, matchday.league)
            stats = PlayerStat.objects.filter(matchday=matchday).select_related("player")
            return Response(PlayerStatResponseSerializer(stats, many=True).data)

        league_services.assert_league_creator_or_admin(request.user, matchday.league)
        serializer = PlayerStatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        player = ProPlayer.objects.filter(pk=data["playerId"]).first()
        if player is None:
            raise ResourceNotFound(f"Player non trovato con id: {data['playerId']}")
        with transaction.atomic():
            stat, _ = PlayerStat.objects.update_or_create(
                matchday=matchday, player=player,
                defaults={
                    "kills": data["kills"], "morti": data["morti"], "assist": data["assist"],
                    "cs": data["cs"], "vision_score": data["visionScore"],
                    "vittoria": data["vittoria"], "wins": 1 if data["vittoria"] else 0,
                    "games_played": data["gamesPlayed"],
                },
            )
            stat.recompute()
            stat.save(update_fields=["fantavoto"])
        return Response(PlayerStatResponseSerializer(stat).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="chiudi")
    def chiudi(self, request, pk=None):
        matchday = services.close_matchday(request.user, pk)
        return Response(MatchdayResponseSerializer(matchday).data)

    @action(detail=True, methods=["post"], url_path="waiting-for-postponed")
    def waiting_for_postponed(self, request, pk=None):
        matchday = services.mark_waiting_for_postponed(request.user, pk)
        return Response(MatchdayResponseSerializer(matchday).data)


class LineupWindowView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fanta_team_id=None):
        return Response(services.lineup_window_status(request.user, fanta_team_id))


class LineupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fanta_team_id=None):
        return Response(services.find_lineup(request.user, fanta_team_id))

    def put(self, request, fanta_team_id=None):
        serializer = LineupRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(services.schedule_lineup(
            request.user, fanta_team_id, serializer.validated_data["titolariIds"]))


class FormationHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fanta_team_id=None):
        return Response(services.formation_history(request.user, fanta_team_id))


class FormationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fanta_team_id=None, matchday_id=None):
        formation = (Formation.objects.prefetch_related("titolari")
                     .filter(fanta_team_id=fanta_team_id, matchday_id=matchday_id).first())
        if formation is None:
            raise ResourceNotFound(
                "Nessuna formazione trovata per la squadra e la giornata indicate")
        services.get_fanta_team(request.user, fanta_team_id)
        return Response(services.formation_payload(formation))


class FormationConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, fanta_team_id=None, matchday_id=None):
        serializer = FormationRequestSerializer(
            data={**request.data, "matchdayId": matchday_id})
        serializer.is_valid(raise_exception=True)
        formation = services.confirm_formation(
            request.user, fanta_team_id, matchday_id, serializer.validated_data["titolariIds"])
        return Response(services.formation_payload(formation), status=status.HTTP_201_CREATED)


class FormationConfirmAllView(APIView):
    """`/api/admin/leagues/{leagueId}/matchdays/{matchdayId}/formations/confirm-all`."""

    permission_classes = [IsAuthenticated]

    def post(self, request, league_id=None, matchday_id=None):
        return Response(services.confirm_all_formations(request.user, league_id, matchday_id))
