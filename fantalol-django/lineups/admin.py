from django.contrib import admin

from .models import LineupPeriod


@admin.register(LineupPeriod)
class LineupPeriodAdmin(admin.ModelAdmin):
    list_display = ("id", "fanta_team", "role", "player", "valid_from", "valid_to", "origin")
    list_filter = ("role", "origin")
