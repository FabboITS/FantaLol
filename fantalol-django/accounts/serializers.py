"""Serializer auth/profilo: stessi campi JSON dei DTO Spring."""
from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.exceptions import BusinessRuleError

from .models import User, UserProfile


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=50)
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise BusinessRuleError(f"Username già in uso: {value}")
        return value

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise BusinessRuleError(f"Email già registrata: {value}")
        return value

    def create(self, validated_data) -> User:
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if user is None:
            raise BusinessRuleError("Credenziali non valide")
        attrs["user"] = user
        return attrs


class FantaLolTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token


class UserProfileSerializer(serializers.ModelSerializer):
    nomeVisualizzato = serializers.CharField(source="nome_visualizzato", max_length=60,
                                             required=False, allow_null=True, allow_blank=True)
    avatarUrl = serializers.CharField(source="avatar_url", max_length=255,
                                      required=False, allow_null=True, allow_blank=True)
    summonerName = serializers.CharField(source="summoner_name", max_length=60,
                                         required=False, allow_null=True, allow_blank=True)
    bio = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ["nomeVisualizzato", "bio", "avatarUrl", "summonerName"]


class UserResponseSerializer(serializers.ModelSerializer):
    nomeVisualizzato = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "nomeVisualizzato"]

    def get_nomeVisualizzato(self, user: User):
        profile = getattr(user, "profile", None)
        return profile.nome_visualizzato if profile else None


class UserDirectoryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email"]
