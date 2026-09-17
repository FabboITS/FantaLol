"""Endpoint auth/profilo: `/api/auth/**` e `/api/users/**`."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import IsGlobalAdmin

from .models import User, UserProfile
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserDirectoryEntrySerializer,
    UserProfileSerializer,
    UserResponseSerializer,
)


def _auth_response(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["username"] = user.username
    refresh["role"] = user.role
    return {
        "token": str(refresh.access_token),
        "refreshToken": str(refresh),
        "tokenType": "Bearer",
        "username": user.username,
        "role": user.role,
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(request=RegisterSerializer, responses=None)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_auth_response(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(request=LoginSerializer, responses=None)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(_auth_response(serializer.validated_data["user"]))


class RefreshView(APIView):
    """Refresh JWT: non esisteva in Spring (token stateless a scadenza unica),
    aggiunto perché richiesto dal contratto `auth/` della nuova API."""

    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data["tokenType"] = "Bearer"
        data["token"] = data.pop("access")
        if "refresh" in data:
            data["refreshToken"] = data.pop("refresh")
        return Response(data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserResponseSerializer(request.user).data)


class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return Response(UserResponseSerializer(request.user).data)


class UserDirectoryView(APIView):
    """`/api/admin/users`: directory utenti riservata all'ADMIN globale."""

    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        users = User.objects.all().order_by("username")
        return Response(UserDirectoryEntrySerializer(users, many=True).data)
