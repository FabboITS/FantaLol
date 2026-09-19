from django.contrib import admin

from .models import ProPlayer, ProTeam


@admin.register(ProTeam)
class ProTeamAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "sigla", "competition", "leaguepedia_name")
    list_filter = ("competition",)
    search_fields = ("nome", "sigla", "leaguepedia_name")


@admin.register(ProPlayer)
class ProPlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "nickname", "ruolo", "team", "competition", "quotazione", "is_worlds_eligible")
    list_filter = ("competition", "ruolo", "is_worlds_eligible")
    search_fields = ("nickname", "nome_reale", "leaguepedia_link")
