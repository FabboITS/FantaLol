from django.db import models

from apps.common.utils import PlayerRole
from apps.esports.models import ProPlayer
from apps.leagues.models import FantaTeam


class LineupPeriodOrigin(models.TextChoices):
    USER = "USER"
    AUTOMATIC = "AUTOMATIC"
    BACKFILL = "BACKFILL"


class EffectiveLineupPeriod(models.Model):
    """Periodo in cui un player è stato titolare in uno slot di ruolo: unica fonte per attribuire i punti."""

    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="lineup_periods")
    role = models.CharField(max_length=10, choices=PlayerRole.choices)
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="+")
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    origin = models.CharField(max_length=20, choices=LineupPeriodOrigin.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "effective_lineup_periods"
        ordering = ["fanta_team_id", "effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["fanta_team", "role", "effective_from"], name="uniq_lineup_period"
            )
        ]
        indexes = [
            models.Index(fields=["fanta_team", "role", "effective_from"], name="idx_lineup_period_active")
        ]

    def active_at(self, instant) -> bool:
        return self.effective_from <= instant and (
            self.effective_until is None or self.effective_until > instant
        )
