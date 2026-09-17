from django.contrib import admin

from .models import AuctionSession, FantaTeam, League, RosterEntry


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "competition", "codice_invito", "admin", "auction_open",
                    "participant_count", "status")
    list_filter = ("competition", "status", "auction_open")
    search_fields = ("nome", "codice_invito")


@admin.register(FantaTeam)
class FantaTeamAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "league", "owner", "crediti_residui", "punti")
    search_fields = ("nome", "owner__username")


@admin.register(RosterEntry)
class RosterEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "fanta_team", "player", "crediti_spesi", "data_acquisto")


@admin.register(AuctionSession)
class AuctionSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "league", "player", "current_bid", "highest_bidder", "status", "ends_at")
    list_filter = ("status",)
