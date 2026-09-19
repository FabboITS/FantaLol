from django.contrib import admin

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "enabled", "created_at")
    list_filter = ("role", "enabled")
    search_fields = ("username", "email")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "nome_visualizzato", "summoner_name")
    search_fields = ("user__username", "nome_visualizzato")
