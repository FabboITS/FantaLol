"""Modalità Worlds: formato event-based ispirato al Fantacalcio Champions League.

Differenze strutturali rispetto alle leghe stagionali (`leagues/`):
 - il player pool è l'unione dei roster qualificati, quindi **non** vincolato a
   un solo competitivo;
 - la "giornata" è la **fase** del torneo: la formazione si conferma prima
   dell'inizio della prima serie di ogni fase;
 - budget e taglia rosa sono configurabili per edizione, non dedotti dal numero
   di partecipanti;
 - la classifica è separata da quelle stagionali e ammette bonus torneo.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from teams.models import PlayerRole, ProPlayer, ProTeam


def generate_invite_code() -> str:
    return uuid.uuid4().hex[:8].upper()


class WorldsEdition(models.Model):
    """Una edizione del mondiale, es. "Worlds 2026"."""

    nome = models.CharField(max_length=100, unique=True)
    anno = models.PositiveIntegerField()
    #: Torneo PandaScore di riferimento (le fasi ne importano le serie).
    pandascore_tournament_id = models.BigIntegerField(blank=True, null=True)
    qualified_teams = models.ManyToManyField(ProTeam, related_name="worlds_editions", blank=True)
    #: Parametri di default per le leghe Worlds di questa edizione.
    default_crediti = models.PositiveIntegerField(default=500)
    default_roster_size = models.PositiveIntegerField(default=10)
    default_max_per_role = models.PositiveIntegerField(default=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "worlds_editions"
        ordering = ["-anno", "nome"]

    def __str__(self) -> str:
        return self.nome


class WorldsStage(models.Model):
    """Fase del torneo: Play-In, Swiss/gruppi, Quarti, Semifinali, Finale.

    Ogni fase è l'equivalente di una "giornata" del Fantacalcio Champions:
    la formazione va confermata entro `lineup_deadline`.
    """

    edition = models.ForeignKey(WorldsEdition, on_delete=models.CASCADE, related_name="stages")
    nome = models.CharField(max_length=80)
    ordine = models.PositiveIntegerField()
    #: Torneo PandaScore specifico della fase, quando differisce da quello dell'edizione.
    pandascore_tournament_id = models.BigIntegerField(blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    #: Deadline formazione: di default l'inizio della prima serie della fase.
    lineup_deadline = models.DateTimeField(blank=True, null=True)
    lineups_locked = models.BooleanField(default=False)
    #: Bonus riconosciuto a chi schiera un player la cui squadra avanza di fase.
    advancement_bonus = models.FloatField(default=2.0)

    class Meta:
        db_table = "worlds_stages"
        ordering = ["edition_id", "ordine"]
        constraints = [
            models.UniqueConstraint(fields=["edition", "ordine"], name="uq_worlds_stage_order"),
        ]

    def __str__(self) -> str:
        return f"{self.edition.nome} - {self.nome}"

    def effective_deadline(self):
        """Deadline esplicita, altrimenti l'inizio della prima serie della fase."""
        if self.lineup_deadline:
            return self.lineup_deadline
        first = self.matches.order_by("begin_at").first()
        return first.begin_at if first else self.starts_at


class WorldsLeague(models.Model):
    """Lega privata Worlds: stessa meccanica di invito delle leghe stagionali."""

    nome = models.CharField(max_length=100)
    codice_invito = models.CharField(max_length=12, unique=True, default=generate_invite_code)
    edition = models.ForeignKey(WorldsEdition, on_delete=models.CASCADE, related_name="leagues")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="worlds_leghe_amministrate")
    crediti_iniziali = models.PositiveIntegerField()
    #: Taglia rosa fissa e configurabile (il torneo è breve: nessuna soglia 2-5/6-10).
    #: Default di edizione: 10 player, 2 per ruolo, di cui 5 titolari per fase.
    roster_size = models.PositiveIntegerField()
    max_per_role = models.PositiveIntegerField()
    auction_open = models.BooleanField(default=False)
    #: Se True, fra una fase e l'altra si può sostituire liberamente un player
    #: della rosa (non solo quelli con squadra eliminata), pagandone la quotazione.
    allow_reentry_swap = models.BooleanField(default=True)
    #: Bonus fantapunti per l'MVP di serie (dato Leaguepedia).
    mvp_bonus = models.FloatField(default=3.0)
    #: Bonus per ogni serie vinta dalla squadra pro di un titolare.
    series_win_bonus = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "worlds_leagues"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.nome


class WorldsTeam(models.Model):
    """FantaTeam di una lega Worlds."""

    nome = models.CharField(max_length=80)
    league = models.ForeignKey(WorldsLeague, on_delete=models.CASCADE, related_name="teams")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="worlds_teams")
    crediti_residui = models.IntegerField()

    class Meta:
        db_table = "worlds_teams"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["league", "owner"], name="uq_worlds_team_league_owner"),
        ]

    def __str__(self) -> str:
        return self.nome


class WorldsRosterEntry(models.Model):
    fanta_team = models.ForeignKey(WorldsTeam, on_delete=models.CASCADE, related_name="rosa")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="worlds_roster_entries")
    crediti_spesi = models.PositiveIntegerField(default=0)
    data_acquisto = models.DateTimeField(auto_now_add=True)
    #: Fase da cui l'ingaggio è valido (per le sostituzioni fra fasi).
    acquired_from_stage = models.ForeignKey(WorldsStage, on_delete=models.SET_NULL,
                                            blank=True, null=True, related_name="+")
    #: Valorizzata quando il player viene sostituito con il jolly.
    released_at_stage = models.ForeignKey(WorldsStage, on_delete=models.SET_NULL,
                                          blank=True, null=True, related_name="+")

    class Meta:
        db_table = "worlds_roster_entries"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["fanta_team", "player"], name="uq_worlds_roster_team_player"),
        ]

    def __str__(self) -> str:
        return f"{self.player.nickname} @ {self.fanta_team.nome}"


class WorldsStageLineup(models.Model):
    """Formazione confermata da un team per una fase del torneo."""

    fanta_team = models.ForeignKey(WorldsTeam, on_delete=models.CASCADE, related_name="lineups")
    stage = models.ForeignKey(WorldsStage, on_delete=models.CASCADE, related_name="lineups")
    titolari = models.ManyToManyField(ProPlayer, related_name="worlds_lineups",
                                      db_table="worlds_stage_lineup_titolari")
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    #: Punteggio della fase, ricalcolato a ogni enrich delle serie.
    punteggio = models.FloatField(default=0.0)
    bonus = models.FloatField(default=0.0)

    class Meta:
        db_table = "worlds_stage_lineups"
        constraints = [
            models.UniqueConstraint(fields=["fanta_team", "stage"], name="uq_worlds_lineup_team_stage"),
        ]

    def __str__(self) -> str:
        return f"{self.fanta_team.nome} - {self.stage.nome}"

    @property
    def totale(self) -> float:
        return self.punteggio + self.bonus


class WorldsAuctionStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "ACTIVE"
    WON = "WON", "WON"
    EXPIRED = "EXPIRED", "EXPIRED"


class WorldsAuctionSession(models.Model):
    league = models.ForeignKey(WorldsLeague, on_delete=models.CASCADE, related_name="auctions")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="worlds_auctions")
    highest_bidder = models.ForeignKey(WorldsTeam, on_delete=models.SET_NULL, blank=True, null=True,
                                       related_name="auctions_won")
    current_bid = models.PositiveIntegerField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=WorldsAuctionStatus.choices,
                              default=WorldsAuctionStatus.ACTIVE)

    class Meta:
        db_table = "worlds_auction_sessions"
        ordering = ["-id"]
        indexes = [models.Index(fields=["status", "ends_at"])]


ROLE_CHOICES = PlayerRole.choices
