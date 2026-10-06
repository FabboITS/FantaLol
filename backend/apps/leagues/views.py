from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.utils import int_param
from apps.esports.competition_data import cumulative_freshness
from apps.scoring import cumulative

from . import auctions, services


class LeagueRequest(serializers.Serializer):
    nome = serializers.CharField(
        max_length=100,
        error_messages={
            "blank": "Il nome della lega è obbligatorio",
            "required": "Il nome della lega è obbligatorio",
        },
    )
    crediti_iniziali = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        error_messages={"min_value": "I crediti iniziali devono essere positivi"},
    )
    competition = serializers.CharField(max_length=16, required=False, allow_blank=True, allow_null=True)
    edition_id = serializers.IntegerField(required=False, allow_null=True)
    settings = serializers.DictField(required=False, allow_null=True)


class JoinRequest(serializers.Serializer):
    codice_invito = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "Il codice invito è obbligatorio",
            "required": "Il codice invito è obbligatorio",
        },
    )
    nome_squadra = serializers.CharField(
        max_length=80,
        error_messages={
            "blank": "Il nome della squadra è obbligatorio",
            "required": "Il nome della squadra è obbligatorio",
        },
    )


class AuctionStartRequest(serializers.Serializer):
    league_id = serializers.IntegerField()
    lec_player_id = serializers.IntegerField(required=False)
    player_id = serializers.IntegerField(required=False)
    fanta_team_id = serializers.IntegerField()

    def validate(self, attrs):
        if attrs.get("lec_player_id") is None and attrs.get("player_id") is None:
            raise serializers.ValidationError({"lec_player_id": "Il player è obbligatorio"})
        return attrs


class BidRequest(serializers.Serializer):
    fanta_team_id = serializers.IntegerField()
    credits = serializers.IntegerField(min_value=1)


def _validated(serializer_class, payload):
    serializer = serializer_class(data=payload)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# --------------------------------------------------------------------------- leghe
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def leagues(request):
    if request.method == "POST":
        values = _validated(LeagueRequest, request.data)
        league = services.create_league(
            request.user,
            nome=values["nome"],
            edition_id=values.get("edition_id"),
            competition=values.get("competition"),
            crediti_iniziali=values.get("crediti_iniziali"),
            league_settings=values.get("settings"),
        )
        return Response(services.league_response(league), status=status.HTTP_201_CREATED)
    return Response(
        [services.league_response(league) for league in services.accessible_leagues(request.user)]
    )


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def league_detail(request, league_id):
    if request.method == "DELETE":
        services.delete_league(request.user, league_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    league = services.get_league(league_id)
    services.assert_can_view(request.user, league)
    return Response(services.league_response(league))


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def auction_phase(request, league_id, action):
    league = (services.open_auction if action == "open" else services.close_auction)(request.user, league_id)
    return Response(services.league_response(league))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_randomly(request, league_id):
    teams = services.complete_all_rosters_randomly(request.user, league_id)
    return Response([services.fanta_team_response(team) for team in teams])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cumulative_ranking(request, league_id):
    league = services.get_league(league_id)
    services.assert_can_view(request.user, league)
    freshness = cumulative_freshness(league.edition.competition)
    if league.is_worlds:
        from apps.worlds.services import ranking

        return Response({**freshness, "ruleset": league.ruleset, "items": ranking(league)})
    return Response({**freshness, "ruleset": league.ruleset, "items": cumulative.league_ranking(league)})


# --------------------------------------------------------------------------- FantaTeam
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join(request):
    values = _validated(JoinRequest, request.data)
    team = services.join_league(request.user, values["codice_invito"], values["nome_squadra"])
    return Response(services.fanta_team_response(team), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_teams(request):
    return Response([services.fanta_team_response(t) for t in services.my_teams(request.user)])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def team_detail(request, team_id):
    return Response(services.fanta_team_response(services.team_for_viewer(request.user, team_id)))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teams_by_league(request, league_id):
    return Response(
        [services.fanta_team_response(t) for t in services.teams_by_league(request.user, league_id)]
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def free_player(request, team_id):
    entry = services.free_player(request.user, team_id)
    return Response(services.roster_entry_response(entry), status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def release_player(request, team_id, entry_id):
    services.release_player(request.user, team_id, entry_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cumulative_score(request, team_id):
    team = services.team_for_viewer(request.user, team_id)
    return Response(cumulative.team_score(team))


# --------------------------------------------------------------------------- aste
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def active_auction(request):
    league_id = int_param(
        request.query_params.get("leagueId") or request.query_params.get("league_id"),
        "leagueId",
        required=True,
    )
    return Response(auctions.auction_response(auctions.active(league_id)))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_auction(request):
    values = _validated(AuctionStartRequest, request.data)
    player_id = values.get("lec_player_id") or values.get("player_id")
    auction = auctions.start(request.user, values["league_id"], player_id, values["fanta_team_id"])
    return Response(auctions.auction_response(auction), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bid(request, auction_id):
    values = _validated(BidRequest, request.data)
    auction = auctions.bid_or_finalize(request.user, auction_id, values["fanta_team_id"], values["credits"])
    return Response(auctions.auction_response(auction))
