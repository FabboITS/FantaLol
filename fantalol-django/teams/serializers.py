"""Serializer team/player con le stesse chiavi JSON dei DTO Spring."""
from rest_framework import serializers

from .models import ProPlayer, ProTeam


class ProPlayerSerializer(serializers.ModelSerializer):
    nomeReale = serializers.CharField(source="nome_reale", required=False, allow_null=True, allow_blank=True)
    imageUrl = serializers.CharField(source="image_url", required=False, allow_null=True, allow_blank=True)
    teamId = serializers.PrimaryKeyRelatedField(source="team", queryset=ProTeam.objects.all())
    teamNome = serializers.CharField(source="team.nome", read_only=True)
    isWorldsEligible = serializers.BooleanField(source="is_worlds_eligible", read_only=True)

    class Meta:
        model = ProPlayer
        fields = [
            "id", "nickname", "nomeReale", "nazionalita", "ruolo", "quotazione",
            "teamId", "teamNome", "imageUrl", "competition", "isWorldsEligible",
        ]
        read_only_fields = ["competition"]

    def create(self, validated_data):
        validated_data.setdefault("competition", validated_data["team"].competition)
        return super().create(validated_data)


class ProPlayerNestedSerializer(serializers.ModelSerializer):
    """Variante senza il team, per evitare ricorsione dentro la risposta team."""

    nomeReale = serializers.CharField(source="nome_reale", read_only=True)
    imageUrl = serializers.CharField(source="image_url", read_only=True)
    teamId = serializers.SerializerMethodField()
    teamNome = serializers.SerializerMethodField()

    class Meta:
        model = ProPlayer
        fields = ["id", "nickname", "nomeReale", "nazionalita", "ruolo", "quotazione",
                  "teamId", "teamNome", "imageUrl"]

    def get_teamId(self, obj):
        return None

    def get_teamNome(self, obj):
        return None


class ProTeamSerializer(serializers.ModelSerializer):
    logoUrl = serializers.CharField(source="logo_url", required=False, allow_null=True, allow_blank=True)
    giocatori = ProPlayerNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ProTeam
        fields = ["id", "nome", "sigla", "logoUrl", "competition", "giocatori"]


class ProTeamSummarySerializer(serializers.ModelSerializer):
    logoUrl = serializers.CharField(source="logo_url", read_only=True)

    class Meta:
        model = ProTeam
        fields = ["id", "nome", "sigla", "logoUrl", "competition"]
