from rest_framework import serializers

from .models import Matchday, PlayerStat


class MatchdayRequestSerializer(serializers.Serializer):
    leagueId = serializers.IntegerField()
    numero = serializers.IntegerField(min_value=1)
    descrizione = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    data = serializers.DateField(required=False, allow_null=True)


class MatchdayResponseSerializer(serializers.ModelSerializer):
    leagueId = serializers.IntegerField(source="league_id", read_only=True)
    leagueNome = serializers.CharField(source="league.nome", read_only=True)
    auctionLocked = serializers.SerializerMethodField()

    class Meta:
        model = Matchday
        fields = ["id", "leagueId", "leagueNome", "numero", "descrizione", "data",
                  "chiusa", "status", "auctionLocked"]

    def get_auctionLocked(self, matchday: Matchday) -> bool:
        return not matchday.chiusa and matchday.league.auction_open


class PlayerStatRequestSerializer(serializers.Serializer):
    lecPlayerId = serializers.IntegerField(required=False)
    playerId = serializers.IntegerField(required=False)
    kills = serializers.IntegerField(min_value=0, required=False, default=0)
    morti = serializers.IntegerField(min_value=0, required=False, default=0)
    assist = serializers.IntegerField(min_value=0, required=False, default=0)
    cs = serializers.IntegerField(min_value=0, required=False, default=0)
    visionScore = serializers.IntegerField(min_value=0, required=False, default=0)
    vittoria = serializers.BooleanField(required=False, default=False)
    gamesPlayed = serializers.IntegerField(min_value=1, required=False, default=1)

    def validate(self, attrs):
        if not attrs.get("lecPlayerId") and not attrs.get("playerId"):
            raise serializers.ValidationError("Il player è obbligatorio")
        attrs["playerId"] = attrs.get("playerId") or attrs.get("lecPlayerId")
        return attrs


class PlayerStatResponseSerializer(serializers.ModelSerializer):
    matchdayId = serializers.IntegerField(source="matchday_id", read_only=True)
    lecPlayerId = serializers.IntegerField(source="player_id", read_only=True)
    playerId = serializers.IntegerField(source="player_id", read_only=True)
    lecPlayerNickname = serializers.CharField(source="player.nickname", read_only=True)
    visionScore = serializers.IntegerField(source="vision_score", read_only=True)
    gamesPlayed = serializers.IntegerField(source="games_played", read_only=True)

    class Meta:
        model = PlayerStat
        fields = ["id", "matchdayId", "lecPlayerId", "playerId", "lecPlayerNickname",
                  "kills", "morti", "assist", "cs", "visionScore", "vittoria", "wins",
                  "gamesPlayed", "fantavoto"]


class LineupRequestSerializer(serializers.Serializer):
    titolariIds = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class FormationRequestSerializer(serializers.Serializer):
    matchdayId = serializers.IntegerField()
    titolariIds = serializers.ListField(child=serializers.IntegerField(), allow_empty=True,
                                        required=False, default=list)
