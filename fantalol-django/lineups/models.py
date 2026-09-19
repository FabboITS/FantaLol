"""Storico dei periodi di titolarità (`lineup/EffectiveLineupPeriod`).

Ogni riga dice quale player occupava un dato slot di ruolo di un FantaTeam in
un dato intervallo temporale: i punti già maturati restano quindi legati al
titolare storico e non a quello attuale.
"""
from __future__ import annotations

from django.db import models

from leagues.models import FantaTeam
from teams.models import PlayerRole, ProPlayer


class LineupPeriodOrigin(models.TextChoices):
    USER = "USER", "USER"
    BACKFILL = "BACKFILL", "BACKFILL"
    AUTOMATIC = "AUTOMATIC", "AUTOMATIC"


class LineupPeriod(models.Model):
    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="lineup_periods")
    role = models.CharField(max_length=20, choices=PlayerRole.choices)
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="lineup_periods")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(blank=True, null=True)
    origin = models.CharField(max_length=20, choices=LineupPeriodOrigin.choices,
                              default=LineupPeriodOrigin.USER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lineup_periods"
        ordering = ["fanta_team_id", "role", "valid_from"]
        constraints = [
            models.UniqueConstraint(fields=["fanta_team", "role", "valid_from"],
                                    name="uq_lineup_period_slot"),
        ]
        indexes = [models.Index(fields=["fanta_team", "role", "valid_from"])]

    def __str__(self) -> str:
        return f"{self.fanta_team_id}/{self.role} -> {self.player_id}"

    def active_at(self, moment) -> bool:
        return self.valid_from <= moment and (self.valid_to is None or self.valid_to > moment)

    def close_at(self, moment) -> None:
        self.valid_to = moment
