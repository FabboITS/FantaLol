from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import BusinessRuleException
from apps.common.permissions import IsGlobalAdmin
from apps.leagues.services import assert_can_view, get_league, get_team

from . import services


class TransferRequest(serializers.Serializer):
    player_out_id = serializers.IntegerField(required=False, allow_null=True)
    player_in_id = serializers.IntegerField(required=False, allow_null=True)


class PriceRequest(serializers.Serializer):
    quotazione = serializers.IntegerField(min_value=1)
    edition_id = serializers.IntegerField(required=False, allow_null=True)


def _worlds_league(user, league_id):
    league = get_league(league_id)
    assert_can_view(user, league)
    if not league.is_worlds:
        raise BusinessRuleException("La lega non usa il regolamento WORLDS")
    return league


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def market(request, league_id):
    return Response(services.market(_worlds_league(request.user, league_id)))


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def transfers(request, team_id):
    team = get_team(team_id)
    _worlds_league(request.user, team.league_id)
    if request.method == "POST":
        serializer = TransferRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = services.make_transfer(
            request.user,
            team_id,
            serializer.validated_data.get("player_out_id"),
            serializer.validated_data.get("player_in_id"),
        )
        return Response(services.transfer_response(transfer), status=status.HTTP_201_CREATED)
    return Response(services.transfer_summary(team))


@api_view(["POST"])
@permission_classes([IsGlobalAdmin])
def publish_listone(request, edition_id):
    edition = services.publish_listone(edition_id)
    return Response({"edition_id": edition.id, "listone_published_at": edition.listone_published_at})


@api_view(["PUT"])
@permission_classes([IsGlobalAdmin])
def set_price(request, player_id):
    serializer = PriceRequest(data=request.data)
    serializer.is_valid(raise_exception=True)
    entry = services.set_price(
        player_id, serializer.validated_data["quotazione"], serializer.validated_data.get("edition_id")
    )
    return Response(
        {"player_id": entry.player_id, "edition_id": entry.edition_id, "quotazione": entry.quotazione}
    )
