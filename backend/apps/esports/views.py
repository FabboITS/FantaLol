from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import IsGlobalAdmin, PublicReadAdminWrite
from apps.common.utils import ROLE_VALUES, int_param, now
from apps.competitions.models import Competition
from apps.scoring import cumulative

from . import admin_services, catalog
from . import competition_data as data
from .models import Provider, ProviderSyncState


# --------------------------------------------------------------------------- serializers
class TeamRequest(serializers.Serializer):
    nome = serializers.CharField(
        max_length=120,
        error_messages={
            "blank": "Il nome del team è obbligatorio",
            "required": "Il nome del team è obbligatorio",
        },
    )
    sigla = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    logo_url = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)


class PlayerRequest(serializers.Serializer):
    nickname = serializers.CharField(
        max_length=60,
        error_messages={"blank": "Il nickname è obbligatorio", "required": "Il nickname è obbligatorio"},
    )
    nome_reale = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)
    nazionalita = serializers.CharField(max_length=60, required=False, allow_blank=True, allow_null=True)
    ruolo = serializers.ChoiceField(
        choices=ROLE_VALUES, error_messages={"required": "Il ruolo è obbligatorio"}
    )
    quotazione = serializers.IntegerField(
        min_value=1, error_messages={"required": "La quotazione è obbligatoria"}
    )
    team_id = serializers.IntegerField(error_messages={"required": "Il team è obbligatorio"})
    image_url = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    edition_id = serializers.IntegerField(required=False, allow_null=True)


class CorrectionRequest(serializers.Serializer):
    participated = serializers.BooleanField(required=False, allow_null=True, default=None)
    kills = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    deaths = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    assists = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    cs = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    vision_score = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    win = serializers.BooleanField(required=False, allow_null=True, default=None)
    champion = serializers.CharField(max_length=60, required=False, allow_blank=True, allow_null=True)


def _validated(serializer_class, payload):
    serializer = serializer_class(data=payload)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# --------------------------------------------------------------------------- competizioni
def edition_item(edition) -> dict:
    return {
        "id": edition.id,
        "competition": edition.competition.code,
        "year": edition.year,
        "name": edition.name,
        "starts_at": edition.starts_at,
        "ends_at": edition.ends_at,
        "is_active": edition.is_active,
        "ruleset": edition.competition.ruleset,
        "scoring_formula_version": edition.scoring_formula_version,
        "lineup_strategy": edition.get_lineup_policy().strategy,
        "listone_published_at": edition.listone_published_at,
        "stages": [
            {
                "code": s.code,
                "order": s.order,
                "starts_at": s.starts_at,
                "ends_at": s.ends_at,
                "max_players_per_team": s.max_players_per_team,
                "budget_bonus": s.budget_bonus,
            }
            for s in edition.stages.all()
        ],
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def competitions(request):
    items = []
    for comp in Competition.objects.prefetch_related("editions").all():
        current = comp.current_edition()
        items.append(
            {
                "code": comp.code,
                "name": comp.name,
                "region": comp.region,
                "ruleset": comp.ruleset,
                "timezone": comp.timezone,
                "logo": comp.logo or None,
                "current_edition": edition_item(current) if current else None,
            }
        )
    return Response(items)


@api_view(["GET"])
@permission_classes([AllowAny])
def competition_editions(request, code):
    competition = data.get_competition(code)
    now_ = now()
    editions = [
        e
        for e in competition.editions.prefetch_related("stages").order_by("-starts_at")
        if request.query_params.get("all") == "true"
        or e.is_active
        or (e.ends_at is None or e.ends_at >= now_)
    ]
    return Response([edition_item(e) for e in editions])


# --------------------------------------------------------------------------- team e player
@api_view(["GET", "POST"])
@permission_classes([PublicReadAdminWrite])
def teams(request):
    if request.method == "POST":
        team = catalog.create_team(_validated(TeamRequest, request.data))
        return Response(catalog.team_summary(team), status=status.HTTP_201_CREATED)
    return Response(
        catalog.list_teams(
            request.query_params.get("competition"), int_param(request.query_params.get("edition"), "edition")
        )
    )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([PublicReadAdminWrite])
def team_detail(request, team_id):
    if request.method == "PUT":
        return Response(
            catalog.team_summary(catalog.update_team(team_id, _validated(TeamRequest, request.data)))
        )
    if request.method == "DELETE":
        catalog.delete_team(team_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(catalog.team_detail(team_id, int_param(request.query_params.get("edition"), "edition")))


@api_view(["GET", "POST"])
@permission_classes([PublicReadAdminWrite])
def players(request):
    if request.method == "POST":
        player = catalog.create_player(_validated(PlayerRequest, request.data))
        return Response(catalog.player_detail(player.id), status=status.HTTP_201_CREATED)
    params = request.query_params
    role = params.get("role") or params.get("ruolo")
    if role and role.upper() not in ROLE_VALUES:
        raise ValidationError({"role": "Ruolo non valido"})
    team = int_param(params.get("team") or params.get("teamId"), "team")
    return Response(
        catalog.list_players(
            params.get("competition"), int_param(params.get("edition"), "edition"), role, team
        )
    )


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([PublicReadAdminWrite])
def player_detail(request, player_id):
    if request.method == "PUT":
        catalog.update_player(player_id, _validated(PlayerRequest, request.data))
        return Response(catalog.player_detail(player_id))
    if request.method == "DELETE":
        catalog.delete_player(player_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        catalog.player_detail(player_id, int_param(request.query_params.get("edition"), "edition"))
    )


# --------------------------------------------------------------------------- dati per competizione
def _edition(request, competition):
    return data.resolve_edition(competition, int_param(request.query_params.get("edition"), "edition"))


@api_view(["GET"])
@permission_classes([AllowAny])
def standings(request, code="lec"):
    competition = data.get_competition(code)
    items = data.standings(_edition(request, competition))
    return Response(data.section(competition, items, provisional=not items))


@api_view(["GET"])
@permission_classes([AllowAny])
def performances(request, code="lec"):
    competition = data.get_competition(code)
    items = data.performances(_edition(request, competition))
    return Response(data.section(competition, items, provisional=not items))


@api_view(["GET"])
@permission_classes([AllowAny])
def cumulative_performances(request, code="lec"):
    competition = data.get_competition(code)
    edition = _edition(request, competition)
    items = cumulative.player_scores(edition.id) if edition else []
    return Response({**data.cumulative_freshness(competition), "items": items})


@api_view(["GET"])
@permission_classes([AllowAny])
def competition_matches(request, code="lec"):
    competition = data.get_competition(code)
    items = data.matches(_edition(request, competition))
    return Response(data.section(competition, items, provisional=not items))


@api_view(["GET"])
@permission_classes([AllowAny])
def competition_game(request, match_id, game_id, code="lec"):
    competition = data.get_competition(code)
    return Response(data.game(_edition(request, competition), match_id, game_id))


# --------------------------------------------------------------------------- feed pipeline (5.3)
@api_view(["GET"])
@permission_classes([AllowAny])
def esports_matches(request):
    params = request.query_params
    competition = (params.get("competition") or "all").lower()
    if competition not in {"all", "lec", "lck", "lpl", "worlds"}:
        raise ValidationError({"competition": "Valori ammessi: all, lec, lck, lpl, worlds"})
    state = (params.get("state") or "upcoming").lower()
    if state not in data.FEED_STATES:
        raise ValidationError({"state": "Valori ammessi: upcoming, results, live"})
    limit = int_param(params.get("limit"), "limit", minimum=1, maximum=100, default=100)
    response = Response(data.feed(competition, state, limit))
    response["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def esports_match_games(request, match_id):
    response = Response(data.match_games(match_id))
    response["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return response


# --------------------------------------------------------------------------- admin
def synchronization_status(competition: Competition) -> dict:
    states = {s.provider: s for s in ProviderSyncState.objects.filter(competition=competition)}
    providers = []
    for provider in (Provider.PANDASCORE, Provider.LEAGUEPEDIA):
        state = states.get(provider)
        providers.append(
            {
                "provider": provider,
                "status": state.status if state else "AWAITING_DATA",
                "last_attempt_at": state.last_attempt_at if state else None,
                "last_success_at": state.last_success_at if state else None,
                "last_error": (state.last_error or None) if state else None,
                "sync_requested_at": state.sync_requested_at if state else None,
            }
        )
    fresh = data.freshness(competition)
    leaguepedia = states.get(Provider.LEAGUEPEDIA)
    return {
        "competition": competition.code,
        "status": fresh["status"],
        "last_updated_at": fresh["last_updated_at"],
        "provisional": fresh["status"] != "fresh",
        "providers": providers,
        "counts": {
            "inserted_games": leaguepedia.inserted_games if leaguepedia else 0,
            "updated_games": leaguepedia.updated_games if leaguepedia else 0,
            "skipped_games": leaguepedia.skipped_games if leaguepedia else 0,
            "failed_games": leaguepedia.failed_games if leaguepedia else 0,
        },
        "unmatched_players": leaguepedia.unmatched_players if leaguepedia else [],
    }


@api_view(["POST"])
@permission_classes([IsGlobalAdmin])
def synchronize(request, code="lec"):
    """Richiede una sincronizzazione: la esegue lo scheduler entro pochi secondi (le view non chiamano
    mai i provider direttamente)."""
    from apps.providers.sync_state import request_sync

    competition = data.get_competition(code)
    request_sync(competition)
    body = synchronization_status(competition)
    body["completed_at"] = None
    body["requested"] = True
    return Response(body, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsGlobalAdmin])
def synchronization(request, code="lec"):
    return Response(synchronization_status(data.get_competition(code)))


@api_view(["PUT", "DELETE"])
@permission_classes([IsGlobalAdmin])
def correct_player_game(request, game_id, player_id):
    if request.method == "DELETE":
        return Response(admin_services.restore(game_id, player_id))
    values = _validated(CorrectionRequest, request.data)
    return Response(admin_services.correct(game_id, player_id, values, request.user.username))


@api_view(["DELETE"])
@permission_classes([IsGlobalAdmin])
def restore_player_game(request, game_id, player_id):
    return Response(admin_services.restore(game_id, player_id))


class ManualGameRequest(serializers.Serializer):
    game_number = serializers.IntegerField(min_value=1)
    winner_team_id = serializers.IntegerField(required=False, allow_null=True)
    played_at = serializers.DateTimeField(required=False, allow_null=True)


@api_view(["POST"])
@permission_classes([IsGlobalAdmin])
def create_manual_game(request, match_id):
    values = _validated(ManualGameRequest, request.data)
    game = admin_services.create_manual_game(
        match_id, values["game_number"], values.get("winner_team_id"), values.get("played_at")
    )
    return Response(
        {"id": game.id, "match_id": game.match_id, "game_number": game.game_number},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsGlobalAdmin])
def unmatched_stats(request):
    return Response(admin_services.unmatched_stats())


class TeamAliasRequest(serializers.Serializer):
    pandascore_name = serializers.CharField(max_length=120)
    leaguepedia_name = serializers.CharField(max_length=120)
    team_id = serializers.IntegerField(required=False, allow_null=True)


class PlayerAliasRequest(serializers.Serializer):
    leaguepedia_link = serializers.CharField(max_length=160)
    player_id = serializers.IntegerField()


@api_view(["POST"])
@permission_classes([IsGlobalAdmin])
def create_alias(request, kind):
    if kind == "team":
        values = _validated(TeamAliasRequest, request.data)
        alias = admin_services.create_team_alias(
            values["pandascore_name"], values["leaguepedia_name"], values.get("team_id")
        )
        return Response(
            {
                "id": alias.id,
                "pandascore_name": alias.pandascore_name,
                "leaguepedia_name": alias.leaguepedia_name,
                "team_id": alias.team_id,
            },
            status=201,
        )
    if kind == "player":
        values = _validated(PlayerAliasRequest, request.data)
        alias = admin_services.create_player_alias(values["leaguepedia_link"], values["player_id"])
        return Response(
            {"id": alias.id, "leaguepedia_link": alias.leaguepedia_link, "player_id": alias.player_id},
            status=201,
        )
    raise ValidationError({"kind": "Valori ammessi: team, player"})
