"""Leghe fantasy private, FantaTeam, rose e sessioni d'asta.

Porting 1:1 di `league/League`, `league/FantaTeam`, `league/RosterEntry` e
`league/AuctionSession`, con l'aggiunta del competitivo pro associato alla lega.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from teams.models import Competition, ProPlayer


class LeagueStatus(models.TextChoices):
    """Stato del ciclo di vita della lega (`SETUP -> ... -> CLOSED`)."""

    SETUP = "SETUP", "SETUP"
    AUCTION_OPEN = "AUCTION_OPEN", "AUCTION_OPEN"
    AUCTION_CLOSED = "AUCTION_CLOSED", "AUCTION_CLOSED"
    RUNNING = "RUNNING", "RUNNING"
    CLOSED = "CLOSED", "CLOSED"


def generate_invite_code() -> str:
    return uuid.uuid4().hex[:8].upper()


class League(models.Model):
    nome = models.CharField(max_length=100)
    codice_invito = models.CharField(max_length=12, unique=True, default=generate_invite_code)
    crediti_iniziali = models.PositiveIntegerField()
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leghe_amministrate")
    created_at = models.DateTimeField(auto_now_add=True)
    auction_open = models.BooleanField(default=False)
    #: Numero di FantaTeam congelato all'avvio della competizione.
    participant_count = models.PositiveIntegerField(blank=True, null=True)
    #: Campionato pro su cui gioca la lega: mai misto (Worlds ha app dedicata).
    competition = models.CharField(max_length=20, choices=Competition.choices, default=Competition.LEC)
    status = models.CharField(max_length=20, choices=LeagueStatus.choices, default=LeagueStatus.SETUP)

    class Meta:
        db_table = "leagues"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.nome

    @property
    def competition_started(self) -> bool:
        return self.participant_count is not None

    def freeze_participant_count(self, count: int) -> None:
        """Congela il numero di partecipanti (idempotente, come in Java)."""
        if self.participant_count is None:
            self.participant_count = count

    @property
    def roster_limits(self) -> tuple[int, int]:
        """(dimensione rosa, massimo per ruolo) in funzione dei partecipanti.

        2-5 squadre -> 10 player (2 per ruolo); 6-10 squadre -> 5 player
        (1 per ruolo). Identica alla `RosterPolicy` Java.
        """
        count = self.participant_count
        if count is None:
            count = self.fanta_teams.count()
        return (10, 2) if count <= 5 else (5, 1)

    @property
    def has_fixed_roster(self) -> bool:
        """True quando la formazione coincide con la rosa (>= 6 partecipanti)."""
        return self.participant_count is not None and self.participant_count >= 6


class FantaTeam(models.Model):
    nome = models.CharField(max_length=80)
    crediti_residui = models.IntegerField()
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="fanta_teams")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fanta_teams")
    punti = models.FloatField(default=0.0)

    class Meta:
        db_table = "fanta_teams"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["league", "owner"], name="uq_fantateam_league_owner"),
        ]

    def __str__(self) -> str:
        return self.nome


class RosterEntry(models.Model):
    """Classe associativa FantaTeam <-> ProPlayer con crediti spesi."""

    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="rosa")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="roster_entries")
    crediti_spesi = models.PositiveIntegerField()
    data_acquisto = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roster_entries"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["fanta_team", "player"], name="uq_roster_team_player"),
        ]

    def __str__(self) -> str:
        return f"{self.player.nickname} @ {self.fanta_team.nome}"


class AuctionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "ACTIVE"
    WON = "WON", "WON"
    EXPIRED = "EXPIRED", "EXPIRED"


class AuctionSession(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="auctions")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="auctions")
    highest_bidder = models.ForeignKey(FantaTeam, on_delete=models.SET_NULL, blank=True, null=True,
                                       related_name="auctions_won")
    current_bid = models.PositiveIntegerField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=AuctionStatus.choices, default=AuctionStatus.ACTIVE)

    class Meta:
        db_table = "auction_sessions"
        ordering = ["-id"]
        indexes = [models.Index(fields=["status", "ends_at"])]

    def __str__(self) -> str:
        return f"Asta {self.player.nickname} ({self.status})"
