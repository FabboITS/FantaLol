from django.contrib import admin

from .models import Formation, ImportedGame, Matchday, PlayerStat


@admin.register(Matchday)
class MatchdayAdmin(admin.ModelAdmin):
    list_display = ("id", "league", "numero", "data", "chiusa", "status")
    list_filter = ("status", "chiusa")


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ("id", "fanta_team", "matchday", "source", "confirmed", "punteggio_totale")
    list_filter = ("source", "confirmed")


@admin.register(PlayerStat)
class PlayerStatAdmin(admin.ModelAdmin):
    list_display = ("id", "matchday", "player", "kills", "morti", "assist", "cs",
                    "vision_score", "wins", "games_played", "fantavoto")


@admin.register(ImportedGame)
class ImportedGameAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "matchday")
