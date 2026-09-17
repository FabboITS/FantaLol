from rest_framework import serializers

from .models import Game, GamePlayerStat, Match, SyncState


class SyncStateSerializer(serializers.ModelSerializer):
    lastAttemptAt = serializers.DateTimeField(source="last_attempt_at", read_only=True)
    lastSuccessAt = serializers.DateTimeField(source="last_success_at", read_only=True)
    lastError = serializers.CharField(source="last_error", read_only=True)

    class Meta:
        model = SyncState
        fields = ["provider", "status", "lastAttemptAt", "lastSuccessAt", "lastError",
                  "inserted", "updated", "skipped", "failed", "details"]


class GamePlayerStatSerializer(serializers.ModelSerializer):
    playerId = serializers.IntegerField(source="player_id", read_only=True)
    nickname = serializers.CharField(source="player.nickname", read_only=True)
    visionScore = serializers.IntegerField(source="effective_vision_score", read_only=True)
    fantasyScore = serializers.FloatField(source="fantasy_score", read_only=True)
    kills = serializers.IntegerField(source="effective_kills", read_only=True)
    deaths = serializers.IntegerField(source="effective_deaths", read_only=True)
    assists = serializers.IntegerField(source="effective_assists", read_only=True)
    cs = serializers.IntegerField(source="effective_cs", read_only=True)
    win = serializers.BooleanField(source="effective_win", read_only=True)

    class Meta:
        model = GamePlayerStat
        fields = ["id", "playerId", "nickname", "role", "champion", "kills", "deaths",
                  "assists", "cs", "gold", "damage", "visionScore", "win", "fantasyScore",
                  "overridden"]


class GameSerializer(serializers.ModelSerializer):
    externalGameId = serializers.CharField(source="external_game_id", read_only=True)
    gameNumber = serializers.IntegerField(source="game_number", read_only=True)
    playedAt = serializers.DateTimeField(source="played_at", read_only=True)
    winnerName = serializers.CharField(source="winner_name", read_only=True)
    mvp = serializers.CharField(source="mvp_link", read_only=True)
    playerStats = GamePlayerStatSerializer(source="player_stats", many=True, read_only=True)

    class Meta:
        model = Game
        fields = ["id", "externalGameId", "gameNumber", "playedAt", "patch", "winnerName",
                  "mvp", "playerStats"]


class MatchSerializer(serializers.ModelSerializer):
    pandascoreId = serializers.IntegerField(source="pandascore_id", read_only=True)
    leagueCode = serializers.CharField(source="league_code", read_only=True)
    beginAt = serializers.DateTimeField(source="begin_at", read_only=True)
    endAt = serializers.DateTimeField(source="end_at", read_only=True)
    numberOfGames = serializers.IntegerField(source="number_of_games", read_only=True)
    winnerName = serializers.CharField(source="winner_name", read_only=True)
    leaguepediaSyncedAt = serializers.DateTimeField(source="leaguepedia_synced_at", read_only=True)
    tournamentName = serializers.CharField(source="tournament_name", read_only=True)

    class Meta:
        model = Match
        fields = ["id", "pandascoreId", "name", "slug", "leagueCode", "tournamentName",
                  "status", "beginAt", "endAt", "numberOfGames", "opponents", "results",
                  "winnerName", "leaguepediaSyncedAt"]


class MatchDetailSerializer(MatchSerializer):
    games = GameSerializer(many=True, read_only=True)

    class Meta(MatchSerializer.Meta):
        fields = MatchSerializer.Meta.fields + ["games"]


class PlayerStatCorrectionSerializer(serializers.Serializer):
    kills = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    deaths = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    assists = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    cs = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    visionScore = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    win = serializers.BooleanField(required=False, allow_null=True)
    participated = serializers.BooleanField(required=False, allow_null=True)
