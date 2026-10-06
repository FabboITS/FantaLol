"""Leghe fantasy, FantaTeam, rose e aste."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.competitions.models import CompetitionEdition, Ruleset
from apps.esports.models import ProPlayer


def _invite_code() -> str:
    return uuid.uuid4().hex[:8].upper()


class League(models.Model):
    nome = models.CharField(max_length=100)
    codice_invito = models.CharField(max_length=12, unique=True, default=_invite_code)
    crediti_iniziali = models.PositiveIntegerField()
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_leagues"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    auction_open = models.BooleanField(default=False)
    participant_count = models.PositiveIntegerField(null=True, blank=True)
    edition = models.ForeignKey(CompetitionEdition, on_delete=models.PROTECT, related_name="leagues")
    ruleset = models.CharField(max_length=16, choices=Ruleset.choices, default=Ruleset.REGIONAL)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "leagues"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.nome

    @property
    def is_worlds(self) -> bool:
        return self.ruleset == Ruleset.WORLDS

    @property
    def competition_started(self) -> bool:
        return self.participant_count is not None

    def freeze_participant_count(self, count: int) -> None:
        if self.participant_count is None:
            self.participant_count = count


class FantaTeam(models.Model):
    nome = models.CharField(max_length=80)
    crediti_residui = models.IntegerField()
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="fanta_teams")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fanta_teams")
    punti = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fanta_teams"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["league", "owner"], name="uniq_team_owner_league")]

    def __str__(self) -> str:
        return self.nome


class RosterEntry(models.Model):
    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="rosa")
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="+")
    player = models.ForeignKey(ProPlayer, on_delete=models.PROTECT, related_name="roster_entries")
    crediti_spesi = models.PositiveIntegerField()
    data_acquisto = models.DateTimeField(auto_now_add=True)
    # True nelle leghe REGIONAL: un player può appartenere a un solo FantaTeam della lega.
    exclusive = models.BooleanField(default=True)

    class Meta:
        db_table = "roster_entries"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["fanta_team", "player"], name="uniq_roster_team_player"),
            models.UniqueConstraint(
                fields=["league", "player"], condition=Q(exclusive=True), name="uniq_exclusive_player_league"
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.league_id:
            self.league_id = self.fanta_team.league_id
        self.exclusive = self.fanta_team.league.ruleset == Ruleset.REGIONAL
        super().save(*args, **kwargs)


class AuctionStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    WON = "WON"
    EXPIRED = "EXPIRED"


class AuctionSession(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="auctions")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="+")
    highest_bidder = models.ForeignKey(FantaTeam, on_delete=models.SET_NULL, null=True, blank=True)
    current_bid = models.PositiveIntegerField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=AuctionStatus.choices, default=AuctionStatus.ACTIVE)

    class Meta:
        db_table = "auction_sessions"
        constraints = [
            models.UniqueConstraint(
                fields=["league"], condition=Q(status="ACTIVE"), name="uniq_active_auction_per_league"
            )
        ]
