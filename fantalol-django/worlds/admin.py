from django.contrib import admin

from .models import (
    WorldsAuctionSession,
    WorldsEdition,
    WorldsLeague,
    WorldsRosterEntry,
    WorldsStage,
    WorldsStageLineup,
    WorldsTeam,
)


class WorldsStageInline(admin.TabularInline):
    model = WorldsStage
    extra = 0


@admin.register(WorldsEdition)
class WorldsEditionAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "anno", "active", "default_crediti", "default_roster_size")
    filter_horizontal = ("qualified_teams",)
    inlines = [WorldsStageInline]


@admin.register(WorldsStage)
class WorldsStageAdmin(admin.ModelAdmin):
    list_display = ("id", "edition", "nome", "ordine", "starts_at", "lineup_deadline",
                    "lineups_locked", "advancement_bonus")
    list_filter = ("edition", "lineups_locked")


@admin.register(WorldsLeague)
class WorldsLeagueAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "edition", "admin", "crediti_iniziali", "roster_size",
                    "max_per_role", "auction_open", "allow_reentry_swap")


@admin.register(WorldsTeam)
class WorldsTeamAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "league", "owner", "crediti_residui")


@admin.register(WorldsRosterEntry)
class WorldsRosterEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "fanta_team", "player", "crediti_spesi", "released_at_stage")


@admin.register(WorldsStageLineup)
class WorldsStageLineupAdmin(admin.ModelAdmin):
    list_display = ("id", "fanta_team", "stage", "confirmed", "punteggio", "bonus")


@admin.register(WorldsAuctionSession)
class WorldsAuctionSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "league", "player", "current_bid", "highest_bidder", "status", "ends_at")
