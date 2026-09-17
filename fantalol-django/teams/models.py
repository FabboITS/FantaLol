"""Squadre e player pro: porting di `team/LecTeam` e `team/LecPlayer`.

Rispetto alla versione Java il modello è multi-lega: ogni squadra dichiara il
competitivo di appartenenza (LEC/LPL/LCK e regioni minori per Worlds).
"""
from __future__ import annotations

from django.db import models


class Competition(models.TextChoices):
    """Competitivi pro supportati.

    LEC/LPL/LCK sono i campionati stagionali su cui si creano le leghe fantasy;
    gli altri servono solo a ospitare i roster qualificati a Worlds.
    """

    LEC = "LEC", "LEC"
    LPL = "LPL", "LPL"
    LCK = "LCK", "LCK"
    LCS = "LCS", "LCS"
    LTA = "LTA", "LTA"
    PCS = "PCS", "PCS"
    VCS = "VCS", "VCS"
    CBLOL = "CBLOL", "CBLOL"
    OTHER = "OTHER", "Altro"


SEASONAL_COMPETITIONS = (Competition.LEC, Competition.LPL, Competition.LCK)


class PlayerRole(models.TextChoices):
    TOP = "TOP", "TOP"
    JUNGLE = "JUNGLE", "JUNGLE"
    MID = "MID", "MID"
    ADC = "ADC", "ADC"
    SUPPORT = "SUPPORT", "SUPPORT"


#: Ordine canonico dei ruoli, usato ovunque serva uno slot per ruolo.
ROLE_ORDER = [
    PlayerRole.TOP,
    PlayerRole.JUNGLE,
    PlayerRole.MID,
    PlayerRole.ADC,
    PlayerRole.SUPPORT,
]


class ProTeam(models.Model):
    """Organizzazione professionistica (ex `LecTeam`)."""

    nome = models.CharField(max_length=80, unique=True)
    sigla = models.CharField(max_length=10, blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    competition = models.CharField(max_length=20, choices=Competition.choices, default=Competition.LEC)
    #: Nome canonico su Leaguepedia, quando differisce da `nome`.
    leaguepedia_name = models.CharField(max_length=120, blank=True, null=True)
    pandascore_id = models.BigIntegerField(blank=True, null=True, db_index=True)

    class Meta:
        db_table = "pro_teams"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class ProPlayer(models.Model):
    """Giocatore professionista (ex `LecPlayer`)."""

    nickname = models.CharField(max_length=60)
    nome_reale = models.CharField(max_length=120, blank=True, null=True)
    nazionalita = models.CharField(max_length=60, blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True, null=True)
    ruolo = models.CharField(max_length=20, choices=PlayerRole.choices)
    #: Quotazione minima d'asta in crediti.
    quotazione = models.PositiveIntegerField()
    team = models.ForeignKey(ProTeam, on_delete=models.CASCADE, related_name="giocatori")
    competition = models.CharField(max_length=20, choices=Competition.choices, default=Competition.LEC)
    #: Chiave `Link` di Leaguepedia, usata per agganciare i box score.
    leaguepedia_link = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    pandascore_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    #: Popolato quando la squadra del player viene importata in un'edizione Worlds.
    is_worlds_eligible = models.BooleanField(default=False)

    class Meta:
        db_table = "pro_players"
        ordering = ["nickname"]
        constraints = [
            models.UniqueConstraint(fields=["nickname", "team"], name="uq_player_nickname_team"),
        ]
        indexes = [models.Index(fields=["competition", "ruolo"])]

    def __str__(self) -> str:
        return self.nickname

    def save(self, *args, **kwargs):
        # Il competitivo del player segue sempre quello della sua squadra.
        if self.team_id and not self.competition:
            self.competition = self.team.competition
        super().save(*args, **kwargs)
