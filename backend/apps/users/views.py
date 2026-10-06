from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.exceptions import api_error
from apps.common.permissions import IsGlobalAdmin

from . import services


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        min_length=3,
        max_length=50,
        error_messages={
            "blank": "Lo username è obbligatorio",
            "required": "Lo username è obbligatorio",
            "min_length": "Lo username deve avere tra 3 e 50 caratteri",
            "max_length": "Lo username deve avere tra 3 e 50 caratteri",
        },
    )
    email = serializers.EmailField(
        max_length=150,
        error_messages={
            "blank": "L'email è obbligatoria",
            "required": "L'email è obbligatoria",
            "invalid": "Formato email non valido",
        },
    )
    password = serializers.CharField(
        min_length=6,
        error_messages={
            "blank": "La password è obbligatoria",
            "required": "La password è obbligatoria",
            "min_length": "La password deve avere almeno 6 caratteri",
        },
    )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        error_messages={"blank": "Lo username è obbligatorio", "required": "Lo username è obbligatorio"}
    )
    password = serializers.CharField(
        error_messages={"blank": "La password è obbligatoria", "required": "La password è obbligatoria"}
    )


class ProfileSerializer(serializers.Serializer):
    nome_visualizzato = serializers.CharField(
        max_length=60, required=False, allow_null=True, allow_blank=True
    )
    bio = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    avatar_url = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    summoner_name = serializers.CharField(max_length=60, required=False, allow_null=True, allow_blank=True)


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    data = RegisterSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    user = services.register(**data.validated_data)
    return Response(services.user_response(user), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    data = LoginSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    try:
        return Response(services.login(**data.validated_data))
    except services.InvalidCredentials:
        return Response(api_error(401, "Credenziali non valide", request.path), status=401)


@api_view(["GET"])
@permission_classes([IsGlobalAdmin])
def directory(request):
    return Response(services.regular_user_directory())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(services.user_response(request.user))


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    data = ProfileSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    user = services.update_profile(request.user, data.validated_data)
    return Response(services.user_response(user))
