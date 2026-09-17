from django.contrib import admin

from .models import Game, GamePlayerStat, Match, PlayerAlias, SyncState, TeamAlias


@admin.register(SyncState)
class SyncStateAdmin(admin.ModelAdmin):
    list_display = ("provider", "status", "last_attempt_at", "last_success_at",
                    "inserted", "updated", "failed")


@admin.register(TeamAlias)
class TeamAliasAdmin(admin.ModelAdmin):
    """I mismatch di nome sono dati: si correggono qui, non nel codice."""

    list_display = ("source_name", "canonical_name", "team")
    search_fields = ("source_name", "canonical_name")


@admin.register(PlayerAlias)
class PlayerAliasAdmin(admin.ModelAdmin):
    list_display = ("source_name", "canonical_name", "player")
    search_fields = ("source_name", "canonical_name")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("pandascore_id", "name", "league_code", "status", "begin_at",
                    "leaguepedia_synced_at", "leaguepedia_attempts")
    list_filter = ("league_code", "status")
    search_fields = ("name", "slug")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("external_game_id", "match", "game_number", "played_at", "winner_name")
    search_fields = ("external_game_id",)


@admin.register(GamePlayerStat)
class GamePlayerStatAdmin(admin.ModelAdmin):
    list_display = ("game", "player", "role", "kills", "deaths", "assists", "cs",
                    "vision_score", "win", "fantasy_score", "overridden")
    list_filter = ("role", "overridden")
