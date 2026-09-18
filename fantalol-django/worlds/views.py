"""Endpoint `/api/worlds/...`, separati da `/api/leagues/` ma con gli stessi
serializer di player/team dove possibile."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import BusinessRuleError
from core.permissions import IsGlobalAdmin
from teams.serializers import ProPlayerSerializer

from . import services
from .models import WorldsEdition, WorldsTeam
from .serializers import (
    WorldsAuctionSerializer,
    WorldsEditionSerializer,
    WorldsJoinRequestSerializer,
    WorldsLeagueRequestSerializer,
    WorldsLeagueResponseSerializer,
    WorldsLineupRequestSerializer,
    WorldsStageLineupSerializer,
    WorldsStageSerializer,
    WorldsSwapRequestSerializer,
    WorldsTeamSerializer,
)


def _team_queryset():
    return WorldsTeam.objects.select_related("league", "owner").prefetch_related(
        "rosa__player__team")


class EditionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        editions = (WorldsEdition.objects.prefetch_related("stages", "qualified_teams")
                    .all().order_by("-anno"))
        return Response(WorldsEditionSerializer(editions, many=True).data)


class EditionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, edition_id=None):
        edition = services.get_edition_or_404(edition_id)
        return Response(WorldsEditionSerializer(edition).data)


class EditionStagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, edition_id=None):
        edition = services.get_edition_or_404(edition_id)
        stages = edition.stages.all().order_by("ordine")
        return Response({
            "stages": WorldsStageSerializer(stages, many=True).data,
            "currentStageId": getattr(services.current_stage(edition), "id", None),
        })


class EditionPoolView(APIView):
    """Player pool dell'edizione: unione dei roster qualificati, multi-regione."""

    permission_classes = [IsAuthenticated]

    def get(self, request, edition_id=None):
        edition = services.get_edition_or_404(edition_id)
        pool = services.worlds_player_pool(edition).order_by("ruolo", "nickname")
        if request.query_params.get("ruolo"):
            pool = pool.filter(ruolo=request.query_params["ruolo"].upper())
        return Response(ProPlayerSerializer(pool, many=True).data)


class EditionSyncPoolView(APIView):
    """Marca `is_worlds_eligible` sui roster qualificati (admin globale)."""

    permission_classes = [IsGlobalAdmin]

    def post(self, request, edition_id=None):
        edition = services.get_edition_or_404(edition_id)
        updated = services.mark_worlds_pool(edition)
        return Response({"editionId": edition.id, "playersMarked": updated})


class StageImportMatchesView(APIView):
    permission_classes = [IsGlobalAdmin]

    def post(self, request, stage_id=None):
        stage = services.get_stage_or_404(stage_id)
        imported = services.import_stage_matches(stage)
        return Response({"stageId": stage.id, "matchesImported": imported})


class WorldsLeagueListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leagues = services.visible_leagues(request.user)
        return Response(WorldsLeagueResponseSerializer(leagues, many=True).data)

    def post(self, request):
        serializer = WorldsLeagueRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        league = services.create_league(
            request.user, data["editionId"], data["nome"],
            crediti_iniziali=data.get("creditiIniziali"),
            roster_size=data.get("rosterSize"),
            max_per_role=data.get("maxPerRole"),
            allow_reentry_swap=data.get("allowReentrySwap", True),
            mvp_bonus=data.get("mvpBonus", 3.0),
            series_win_bonus=data.get("seriesWinBonus", 1.0),
        )
        return Response(WorldsLeagueResponseSerializer(league).data, status=status.HTTP_201_CREATED)


class WorldsLeagueDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, league_id=None):
        league = services.get_league_or_404(league_id)
        services.assert_can_view(request.user, league)
        return Response(WorldsLeagueResponseSerializer(league).data)


class WorldsLeagueJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WorldsJoinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = services.join_league(request.user, serializer.validated_data["codiceInvito"],
                                    serializer.validated_data["nomeSquadra"])
        return Response(WorldsTeamSerializer(_team_queryset().get(pk=team.pk)).data,
                        status=status.HTTP_201_CREATED)


class WorldsLeagueTeamsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, league_id=None):
        league = services.get_league_or_404(league_id)
        services.assert_can_view(request.user, league)
        return Response(WorldsTeamSerializer(_team_queryset().filter(league=league), many=True).data)


class WorldsLeagueAuctionView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, league_id=None, state=None):
        if state not in {"open", "close"}:
            raise BusinessRuleError("Stato asta non valido")
        league = services.set_auction_open(request.user, league_id, state == "open")
        return Response(WorldsLeagueResponseSerializer(league).data)

    def post(self, request, league_id=None):
        """Avvia l'asta di un player."""
        player_id = request.data.get("playerId")
        team_id = request.data.get("fantaTeamId")
        if not player_id or not team_id:
            raise BusinessRuleError("playerId e fantaTeamId sono obbligatori")
        auction = services.start_auction(request.user, league_id, player_id, team_id)
        return Response(WorldsAuctionSerializer(auction).data, status=status.HTTP_201_CREATED)

    def get(self, request, league_id=None):
        from django.conf import settings

        from .models import WorldsAuctionStatus

        league = services.get_league_or_404(league_id)
        services.assert_can_view(request.user, league)
        # Come per le leghe stagionali: senza worker Celery le aste scadute si
        # chiudono alla prima lettura.
        if settings.FANTALOL["FINALIZE_AUCTIONS_ON_READ"]:
            services.finalize_expired_auctions()
        auction = (league.auctions.select_related("player", "highest_bidder")
                   .filter(status=WorldsAuctionStatus.ACTIVE).order_by("id").first())
        return Response(WorldsAuctionSerializer(auction).data if auction else None)


class WorldsAuctionBidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, auction_id=None):
        team_id = request.data.get("fantaTeamId")
        credits = request.data.get("credits")
        if not team_id or credits is None:
            raise BusinessRuleError("fantaTeamId e credits sono obbligatori")
        auction = services.place_bid(request.user, auction_id, team_id, int(credits))
        return Response(WorldsAuctionSerializer(auction).data)


class WorldsTeamRosterCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, team_id=None):
        team = services.complete_roster_randomly(request.user, team_id)
        return Response(WorldsTeamSerializer(_team_queryset().get(pk=team.pk)).data)


class WorldsSwapView(APIView):
    """Sostituzione libera fra una fase e l'altra (`allow_reentry_swap`)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, league_id=None):
        serializer = WorldsSwapRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        team = services.swap_player(request.user, data["fantaTeamId"],
                                    data["outPlayerId"], data["inPlayerId"])
        return Response(WorldsTeamSerializer(_team_queryset().get(pk=team.pk)).data)


class WorldsLineupView(APIView):
    """`/api/worlds/leagues/{id}/lineup/`: conferma formazione per la fase corrente."""

    permission_classes = [IsAuthenticated]

    def get(self, request, league_id=None):
        league = services.get_league_or_404(league_id)
        services.assert_can_view(request.user, league)
        team = WorldsTeam.objects.filter(league=league, owner=request.user).first()
        if team is None:
            raise BusinessRuleError("Non hai una squadra in questa lega Worlds")
        stage_id = request.query_params.get("stageId")
        stage = (services.get_stage_or_404(stage_id) if stage_id
                 else services.current_stage(league.edition))
        if stage is None:
            raise BusinessRuleError("L'edizione non ha fasi configurate")
        lineup = services.stage_lineup(team, stage)
        return Response({
            "stage": WorldsStageSerializer(stage).data,
            "lineup": WorldsStageLineupSerializer(lineup).data if lineup else None,
            "roster": WorldsTeamSerializer(_team_queryset().get(pk=team.pk)).data["rosa"],
        })

    def post(self, request, league_id=None):
        serializer = WorldsLineupRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        league = services.get_league_or_404(league_id)
        services.assert_can_view(request.user, league)
        stage = (services.get_stage_or_404(data["stageId"]) if data.get("stageId")
                 else services.current_stage(league.edition))
        if stage is None:
            raise BusinessRuleError("L'edizione non ha fasi configurate")
        lineup = services.confirm_stage_lineup(
            request.user, data["fantaTeamId"], stage.id, data["titolariIds"])
        return Response(WorldsStageLineupSerializer(lineup).data, status=status.HTTP_201_CREATED)


class WorldsStandingsView(APIView):
    """`/api/worlds/leagues/{id}/standings/`: classifica separata da quelle stagionali."""

    permission_classes = [IsAuthenticated]

    def get(self, request, league_id=None):
        from django.conf import settings

        league = services.get_league_or_404(league_id)
        services.assert_can_view(request.user, league)
        return Response({
            "leagueId": league.id,
            "edition": league.edition.nome,
            "items": services.standings(league),
            "attribution": settings.LEAGUEPEDIA["ATTRIBUTION"],
        })


class WorldsRecomputeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, league_id=None):
        league = services.get_league_or_404(league_id)
        services.assert_league_admin(request.user, league)
        return Response({"recomputed": services.recompute_league(league)})
