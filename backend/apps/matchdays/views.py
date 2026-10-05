from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsGlobalAdmin, PublicReadAuthenticatedWrite
from apps.common.utils import int_param

from . import formations, services


class MatchdayRequest(serializers.Serializer):
    league_id = serializers.IntegerField(error_messages={"required": "La lega è obbligatoria"})
    numero = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    descrizione = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    data = serializers.DateField(required=False, allow_null=True)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)


class PlayerStatRequest(serializers.Serializer):
    lec_player_id = serializers.IntegerField(error_messages={"required": "Il player è obbligatorio"})
    kills = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    morti = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    assist = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    cs = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    vision_score = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    vittoria = serializers.BooleanField(required=False, default=False)


class FormationRequest(serializers.Serializer):
    matchday_id = serializers.IntegerField(error_messages={"required": "La giornata è obbligatoria"})
    titolari_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        error_messages={"empty": "Devi schierare almeno un titolare"},
    )


class LineupRequest(serializers.Serializer):
    titolari_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        error_messages={
            "empty": "Devi schierare almeno un titolare",
            "required": "Devi schierare almeno un titolare",
        },
    )
    panchina_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    capitano_id = serializers.IntegerField(required=False, allow_null=True)
    vice_capitano_id = serializers.IntegerField(required=False, allow_null=True)


def _validated(serializer_class, payload):
    serializer = serializer_class(data=payload)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# --------------------------------------------------------------------------- giornate
@api_view(["GET", "POST"])
@permission_classes([PublicReadAuthenticatedWrite])
def matchdays(request):
    if request.method == "POST":
        values = _validated(MatchdayRequest, request.data)
        matchday = services.create(
            request.user,
            league_id=values["league_id"],
            numero=values.get("numero"),
            descrizione=values.get("descrizione"),
            data=values.get("data"),
            starts_at=values.get("starts_at"),
            ends_at=values.get("ends_at"),
        )
        return Response(services.matchday_response(matchday), status=status.HTTP_201_CREATED)
    league_id = int_param(request.query_params.get("leagueId"), "leagueId")
    return Response([services.matchday_response(m) for m in services.list_matchdays(league_id)])


@api_view(["GET"])
@permission_classes([PublicReadAuthenticatedWrite])
def matchday_detail(request, matchday_id):
    return Response(services.matchday_response(services.get_matchday(matchday_id)))


@api_view(["GET", "POST"])
@permission_classes([PublicReadAuthenticatedWrite])
def matchday_stats(request, matchday_id):
    if request.method == "POST":
        stat = services.insert_stats(request.user, matchday_id, _validated(PlayerStatRequest, request.data))
        return Response(services.player_stat_response(stat), status=status.HTTP_201_CREATED)
    matchday = services.get_matchday(matchday_id)
    return Response([services.player_stat_response(s) for s in matchday.statistiche.select_related("player")])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close_matchday(request, matchday_id):
    return Response(services.matchday_response(services.close(request.user, matchday_id)))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def waiting_for_postponed(request, matchday_id):
    return Response(services.matchday_response(services.mark_waiting(request.user, matchday_id)))


# --------------------------------------------------------------------------- formazioni
@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def formations_root(request, team_id):
    if request.method == "PUT":
        values = _validated(FormationRequest, request.data)
        return Response(
            formations.imposta(request.user, team_id, values["matchday_id"], values["titolari_ids"])
        )
    return Response(formations.history(team_id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def formation_window(request, team_id):
    return Response(formations.lineup_window(request.user, team_id))


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def formation_lineup(request, team_id):
    if request.method == "PUT":
        return Response(
            formations.schedule_lineup(request.user, team_id, _validated(LineupRequest, request.data))
        )
    return Response(formations.find_lineup(request.user, team_id))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def formation_by_matchday(request, team_id, matchday_id):
    return Response(formations.find_by_team_and_matchday(team_id, matchday_id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_formation(request, team_id, matchday_id):
    return Response(formations.confirm(request.user, team_id, matchday_id))


@api_view(["POST"])
@permission_classes([IsGlobalAdmin])
def confirm_all(request, league_id, matchday_id):
    return Response({"confirmed_teams": formations.confirm_all(request.user, league_id, matchday_id)})
