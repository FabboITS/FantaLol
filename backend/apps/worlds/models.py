from django.db import models

from apps.esports.models import ProPlayer
from apps.leagues.models import FantaTeam
from apps.matchdays.models import Matchday


class Transfer(models.Model):
    """Cambio di mercato WORLDS (acquisto/vendita a prezzo di listone)."""

    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="transfers")
    matchday = models.ForeignKey(Matchday, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    player_out = models.ForeignKey(
        ProPlayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    player_in = models.ForeignKey(
        ProPlayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    price_out = models.PositiveIntegerField(default=0)
    price_in = models.PositiveIntegerField(default=0)
    is_free = models.BooleanField(default=True)
    # Cambio gratuito perché il player venduto appartiene a un team eliminato (non consuma la quota).
    freed_by_elimination = models.BooleanField(default=False)
    penalty_points = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "worlds_transfers"
        ordering = ["created_at", "id"]
