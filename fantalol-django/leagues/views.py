"""Endpoint `/api/leagues`, `/api/fanta-teams`, `/api/auctions`."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core.exceptions import BusinessRuleError
from scoring import services as scoring_services

from . import services
from .models import FantaTeam
from .serializers import (
    AcquistoPlayerRequestSerializer,
    AuctionBidRequestSerializer,
    AuctionResponseSerializer,
    AuctionStartRequestSerializer,
    FantaTeamResponseSerializer,
    JoinLeagueRequestSerializer,
    LeagueRequestSerializer,
    LeagueResponseSerializer,
    RosterEntryResponseSerializer,
)


def _team_queryset():
    return FantaTeam.objects.select_related("league", "owner").prefetch_related("rosa__player")


class LeagueViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        leagues = services.visible_leagues(request.user)
        return Response(LeagueResponseSerializer(leagues, many=True).data)

    def retrieve(self, request, pk=None):
        league = services.get_league_or_404(pk)
        services.assert_can_view_league(request.user, league)
        return Response(LeagueResponseSerializer(league).data)

    def create(self, request):
        serializer = LeagueRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        league = services.create_league(
            request.user,
            serializer.validated_data["nome"],
            serializer.validated_data.get("creditiIniziali"),
            serializer.validated_data.get("competition"),
        )
        return Response(LeagueResponseSerializer(league).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        services.delete_league(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["put"], url_path="auction/open")
    def open_auction(self, request, pk=None):
        league = services.open_auction(request.user, pk)
        return Response(LeagueResponseSerializer(league).data)

    @action(detail=True, methods=["put"], url_path="auction/close")
    def close_auction(self, request, pk=None):
        league = services.close_auction(request.user, pk)
        return Response(LeagueResponseSerializer(league).data)

    @action(detail=True, methods=["post"], url_path="rosters/complete-randomly")
    def complete_rosters(self, request, pk=None):
        teams = services.complete_all_rosters_randomly(request.user, pk)
        ids = [team.id for team in teams]
        refreshed = _team_queryset().filter(id__in=ids)
        return Response(FantaTeamResponseSerializer(refreshed, many=True).data)

    @action(detail=True, methods=["get"], url_path="cumulative-ranking")
    def cumulative_ranking(self, request, pk=None):
        league = services.get_league_or_404(pk)
        services.assert_can_view_league(request.user, league)
        return Response(scoring_services.league_ranking_response(league.id))


class FantaTeamViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        team = services.get_fanta_team_or_404(pk)
        services.assert_can_view_league(request.user, team.league)
        return Response(FantaTeamResponseSerializer(_team_queryset().get(pk=pk)).data)

    @action(detail=False, methods=["post"], url_path="join")
    def join(self, request):
        serializer = JoinLeagueRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = services.join_league(
            request.user,
            serializer.validated_data["codiceInvito"],
            serializer.validated_data["nomeSquadra"],
        )
        return Response(FantaTeamResponseSerializer(_team_queryset().get(pk=team.pk)).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="me")
    def mine(self, request):
        teams = _team_queryset().filter(owner=request.user)
        return Response(FantaTeamResponseSerializer(teams, many=True).data)

    @action(detail=False, methods=["get"], url_path=r"by-league/(?P<league_id>[^/.]+)")
    def by_league(self, request, league_id=None):
        league = services.get_league_or_404(league_id)
        services.assert_can_view_league(request.user, league)
        teams = _team_queryset().filter(league=league)
        return Response(FantaTeamResponseSerializer(teams, many=True).data)

    @action(detail=True, methods=["post"], url_path="rosa")
    def acquista(self, request, pk=None):
        serializer = AcquistoPlayerRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = services.acquista_player(
            request.user, pk,
            serializer.validated_data["playerId"],
            serializer.validated_data["creditiOfferti"],
        )
        return Response(RosterEntryResponseSerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rosa/gratis")
    def acquista_gratis(self, request, pk=None):
        entry = services.acquista_player_gratis(request.user, pk)
        return Response(RosterEntryResponseSerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rosa/completa-casualmente")
    def completa_casualmente(self, request, pk=None):
        team = services.completa_rosa_casualmente(request.user, pk)
        return Response(FantaTeamResponseSerializer(_team_queryset().get(pk=team.pk)).data)

    @action(detail=True, methods=["delete"], url_path=r"rosa/(?P<entry_id>[^/.]+)")
    def rilascia(self, request, pk=None, entry_id=None):
        services.rilascia_player(request.user, pk, entry_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="cumulative-score")
    def cumulative_score(self, request, pk=None):
        team = services.get_fanta_team_or_404(pk)
        services.assert_can_view_league(request.user, team.league)
        return Response(scoring_services.team_score(team.id))


class AuctionActiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        league_id = request.query_params.get("leagueId")
        if not league_id:
            raise BusinessRuleError("Il parametro leagueId è obbligatorio")
        league = services.get_league_or_404(league_id)
        services.assert_can_view_league(request.user, league)
        auction = services.active_auction(league.id)
        if auction is None:
            return Response(None)
        return Response(AuctionResponseSerializer(auction).data)

    def post(self, request):
        serializer = AuctionStartRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        auction = services.start_auction(
            request.user, data["leagueId"], data["playerId"], data["fantaTeamId"])
        return Response(AuctionResponseSerializer(auction).data, status=status.HTTP_201_CREATED)


class AuctionBidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        serializer = AuctionBidRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        auction = services.place_bid(
            request.user, pk,
            serializer.validated_data["fantaTeamId"],
            serializer.validated_data["credits"],
        )
        return Response(AuctionResponseSerializer(auction).data)
