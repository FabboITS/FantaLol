"""Giornate, formazioni per giornata e statistiche aggregate.

Porting di `matchday/Matchday`, `matchday/Formation`, `matchday/PlayerStat` e
`matchday/ImportedGame`.
"""
from __future__ import annotations

from django.db import models

from ingest.models import Game
from leagues.models import FantaTeam, League
from teams.models import ProPlayer


class MatchdayStatus(models.TextChoices):
    OPEN = "OPEN", "OPEN"
    WAITING_FOR_POSTPONED_MATCHES = "WAITING_FOR_POSTPONED_MATCHES", "WAITING_FOR_POSTPONED_MATCHES"
    CLOSED = "CLOSED", "CLOSED"


class Matchday(models.Model):
    numero = models.PositiveIntegerField()
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="matchdays")
    descrizione = models.CharField(max_length=100, blank=True, null=True)
    data = models.DateField(blank=True, null=True)
    chiusa = models.BooleanField(default=False)
    status = models.CharField(max_length=40, choices=MatchdayStatus.choices,
                              default=MatchdayStatus.OPEN)

    class Meta:
        db_table = "matchdays"
        ordering = ["league_id", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["league", "numero"], name="uq_matchday_league_numero"),
        ]

    def __str__(self) -> str:
        return f"Giornata {self.numero} ({self.league.nome})"


class FormationSource(models.TextChoices):
    SUBMITTED = "SUBMITTED", "SUBMITTED"
    CARRIED = "CARRIED", "CARRIED"
    AUTOMATIC = "AUTOMATIC", "AUTOMATIC"
    MISSING = "MISSING", "MISSING"


class Formation(models.Model):
    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="formazioni")
    matchday = models.ForeignKey(Matchday, on_delete=models.CASCADE, related_name="formazioni")
    titolari = models.ManyToManyField(ProPlayer, related_name="formazioni",
                                      db_table="formation_titolari")
    source = models.CharField(max_length=20, choices=FormationSource.choices,
                              default=FormationSource.SUBMITTED)
    confirmed = models.BooleanField(default=False)
    punteggio_totale = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = "formations"
        constraints = [
            models.UniqueConstraint(fields=["fanta_team", "matchday"], name="uq_formation_team_matchday"),
        ]

    def __str__(self) -> str:
        return f"Formazione {self.fanta_team_id} g{self.matchday_id}"


class PlayerStat(models.Model):
    """Statistica aggregata di un player in una giornata (media cumulativa)."""

    matchday = models.ForeignKey(Matchday, on_delete=models.CASCADE, related_name="statistiche")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="matchday_stats")
    kills = models.IntegerField(default=0)
    morti = models.IntegerField(default=0)
    assist = models.IntegerField(default=0)
    cs = models.IntegerField(default=0)
    vision_score = models.IntegerField(default=0)
    vittoria = models.BooleanField(default=False)
    wins = models.IntegerField(default=0)
    games_played = models.IntegerField(default=1)
    fantavoto = models.FloatField(default=0.0)

    class Meta:
        db_table = "player_stats"
        constraints = [
            models.UniqueConstraint(fields=["matchday", "player"], name="uq_playerstat_matchday_player"),
        ]

    def __str__(self) -> str:
        return f"{self.player_id} g{self.matchday_id}"

    def recompute(self) -> float:
        from scoring.calculator import average_score

        self.fantavoto = average_score(
            self.player.ruolo, self.kills, self.morti, self.assist, self.cs,
            self.vision_score, self.wins, self.games_played,
        )
        return self.fantavoto


class ImportedGame(models.Model):
    """Aggancio giornata <-> game di ingest: garantisce import idempotente."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="imports")
    matchday = models.ForeignKey(Matchday, on_delete=models.CASCADE, related_name="imported_games")

    class Meta:
        db_table = "imported_games"
        constraints = [
            models.UniqueConstraint(fields=["game", "matchday"], name="uq_imported_game_matchday"),
        ]
