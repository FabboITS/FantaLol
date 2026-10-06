from django.db import models

from apps.competitions.models import ScoringFormulaVersion, Stage
from apps.esports.models import ProPlayer
from apps.leagues.models import FantaTeam, League


class MatchdayStatus(models.TextChoices):
    OPEN = "OPEN"
    WAITING_FOR_POSTPONED_MATCHES = "WAITING_FOR_POSTPONED_MATCHES"
    CLOSED = "CLOSED"


class Matchday(models.Model):
    numero = models.PositiveIntegerField()
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="matchdays")
    descrizione = models.CharField(max_length=100, blank=True, null=True)
    data = models.DateField(null=True, blank=True)
    chiusa = models.BooleanField(default=False)
    status = models.CharField(max_length=40, choices=MatchdayStatus.choices, default=MatchdayStatus.OPEN)
    # Finestra temporale (UTC) delle serie che appartengono alla giornata.
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    stage = models.ForeignKey(Stage, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    provisional = models.BooleanField(default=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "matchdays"
        ordering = ["league_id", "numero"]
        constraints = [models.UniqueConstraint(fields=["league", "numero"], name="uniq_matchday_number")]

    def __str__(self) -> str:
        return f"{self.league} · G{self.numero}"


class FormationSource(models.TextChoices):
    SUBMITTED = "SUBMITTED"
    CARRIED = "CARRIED"
    AUTOMATIC = "AUTOMATIC"
    MISSING = "MISSING"


class Formation(models.Model):
    fanta_team = models.ForeignKey(FantaTeam, on_delete=models.CASCADE, related_name="formations")
    matchday = models.ForeignKey(Matchday, on_delete=models.CASCADE, related_name="formations")
    titolari = models.ManyToManyField(ProPlayer, related_name="+", blank=True)
    source = models.CharField(
        max_length=20, choices=FormationSource.choices, default=FormationSource.SUBMITTED
    )
    confirmed = models.BooleanField(default=False)
    punteggio_totale = models.FloatField(null=True, blank=True)
    capitano = models.ForeignKey(
        ProPlayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    vice_capitano = models.ForeignKey(
        ProPlayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # WORLDS: id dei panchinari in ordine di priorità.
    bench_order = models.JSONField(default=list, blank=True)
    # WORLDS: esito della chiusura (titolari effettivi dopo le sostituzioni, bonus capitano, penalità).
    effective_titolari = models.JSONField(default=list, blank=True)
    captain_points = models.FloatField(null=True, blank=True)
    penalty_points = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "formations"
        constraints = [models.UniqueConstraint(fields=["fanta_team", "matchday"], name="uniq_formation")]


class PlayerStatSource(models.TextChoices):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class PlayerStat(models.Model):
    """Aggregato per giornata delle statistiche reali di un player."""

    matchday = models.ForeignKey(Matchday, on_delete=models.CASCADE, related_name="statistiche")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="+")
    kills = models.PositiveIntegerField(default=0)
    morti = models.PositiveIntegerField(default=0)
    assist = models.PositiveIntegerField(default=0)
    cs = models.PositiveIntegerField(default=0)
    vision_score = models.PositiveIntegerField(default=0)
    vittoria = models.BooleanField(default=False)
    wins = models.PositiveIntegerField(default=0)
    games_played = models.PositiveIntegerField(default=1)
    series_played = models.PositiveIntegerField(default=1)
    formula_version = models.CharField(
        max_length=32, choices=ScoringFormulaVersion.choices, default=ScoringFormulaVersion.REGIONAL_V1
    )
    fantavoto = models.FloatField()
    source = models.CharField(max_length=10, choices=PlayerStatSource.choices, default=PlayerStatSource.AUTO)
    complete = models.BooleanField(default=True)

    class Meta:
        db_table = "player_stats"
        constraints = [models.UniqueConstraint(fields=["matchday", "player"], name="uniq_player_stat")]
