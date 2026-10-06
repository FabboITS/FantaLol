"""Competizioni, edizioni giocabili, fasi (stage) e politiche di formazione."""

from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.db import models


class Ruleset(models.TextChoices):
    REGIONAL = "REGIONAL", "Regionale"
    WORLDS = "WORLDS", "Worlds"


class ScoringFormulaVersion(models.TextChoices):
    HISTORICAL = "HISTORICAL", "Formula storica"
    REGIONAL_V1 = "REGIONAL_V1", "Regionale v1"
    # Alias storico del backend Java: stesso algoritmo di REGIONAL_V1.
    SUMMER_2026_V1 = "SUMMER_2026_V1", "Summer 2026 v1 (alias di REGIONAL_V1)"


class Competition(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    region = models.CharField(max_length=60)
    ruleset = models.CharField(max_length=16, choices=Ruleset.choices, default=Ruleset.REGIONAL)
    timezone = models.CharField(max_length=64, default="Europe/Rome")
    pandascore_league_id = models.BigIntegerField(null=True, blank=True, unique=True)
    leaguepedia_name = models.CharField(max_length=120, blank=True, default="")
    logo = models.CharField(max_length=255, blank=True, default="")
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "competitions"
        ordering = ["display_order", "code"]

    def __str__(self) -> str:
        return self.code

    def active_editions(self):
        return self.editions.filter(is_active=True).order_by("-starts_at")

    def current_edition(self) -> CompetitionEdition | None:
        return self.active_editions().first() or self.editions.order_by("-starts_at").first()


class LineupStrategy(models.TextChoices):
    FIXED_WEEKLY_WINDOW = "FIXED_WEEKLY_WINDOW", "Finestra settimanale fissa"
    LOCK_BEFORE_FIRST_MATCH = "LOCK_BEFORE_FIRST_MATCH", "Blocco prima della prima serie"


class LineupPolicy(models.Model):
    """Regola per la modifica delle formazioni (giorni ISO: 1 = lunedì ... 7 = domenica)."""

    name = models.CharField(max_length=80, unique=True)
    strategy = models.CharField(max_length=32, choices=LineupStrategy.choices)
    open_day = models.PositiveSmallIntegerField(default=2)
    close_day = models.PositiveSmallIntegerField(default=4)
    effective_day = models.PositiveSmallIntegerField(default=5)
    timezone = models.CharField(max_length=64, blank=True, default="")
    lock_minutes = models.PositiveIntegerField(default=60)

    class Meta:
        db_table = "lineup_policies"

    def __str__(self) -> str:
        return self.name


class CompetitionEdition(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT, related_name="editions")
    year = models.PositiveIntegerField()
    name = models.CharField(max_length=120)
    pandascore_serie_id = models.BigIntegerField(null=True, blank=True)
    pandascore_tournament_ids = ArrayField(models.BigIntegerField(), default=list, blank=True)
    leaguepedia_overview_pages = ArrayField(models.CharField(max_length=200), default=list, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    scoring_formula_version = models.CharField(
        max_length=32, choices=ScoringFormulaVersion.choices, default=ScoringFormulaVersion.REGIONAL_V1
    )
    is_active = models.BooleanField(default=True)
    lineup_policy = models.ForeignKey(LineupPolicy, on_delete=models.PROTECT, null=True, blank=True)
    listone_published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "competition_editions"
        ordering = ["competition__display_order", "-starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["pandascore_serie_id"],
                condition=models.Q(pandascore_serie_id__isnull=False),
                name="uniq_edition_pandascore_serie",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def ruleset(self) -> str:
        return self.competition.ruleset

    def get_lineup_policy(self) -> LineupPolicy:
        if self.lineup_policy_id:
            return self.lineup_policy
        return default_policy_for(self.competition)


class StageCode(models.TextChoices):
    PLAY_IN = "PLAY_IN", "Play-In"
    SWISS = "SWISS", "Swiss Stage"
    QUARTERFINALS = "QUARTERFINALS", "Quarti di finale"
    SEMIFINALS = "SEMIFINALS", "Semifinali"
    FINAL = "FINAL", "Finale"


class Stage(models.Model):
    edition = models.ForeignKey(CompetitionEdition, on_delete=models.CASCADE, related_name="stages")
    code = models.CharField(max_length=20, choices=StageCode.choices)
    order = models.PositiveSmallIntegerField()
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    max_players_per_team = models.PositiveSmallIntegerField(null=True, blank=True)
    free_transfers_unlimited_before = models.BooleanField(default=False)
    budget_bonus = models.IntegerField(default=0)
    pandascore_tournament_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "stages"
        ordering = ["edition_id", "order"]
        constraints = [models.UniqueConstraint(fields=["edition", "code"], name="uniq_stage_code")]

    def __str__(self) -> str:
        return f"{self.edition} · {self.code}"


DEFAULT_WEEKLY_POLICY = "LEC settimanale (mar–gio, effettiva ven)"
DEFAULT_LOCK_POLICY = "Blocco 60 minuti prima della prima serie"


def default_policy_for(competition: Competition) -> LineupPolicy:
    if competition.code == "LEC":
        policy, _ = LineupPolicy.objects.get_or_create(
            name=DEFAULT_WEEKLY_POLICY,
            defaults={
                "strategy": LineupStrategy.FIXED_WEEKLY_WINDOW,
                "open_day": 2,
                "close_day": 4,
                "effective_day": 5,
                "timezone": "Europe/Rome",
            },
        )
        return policy
    policy, _ = LineupPolicy.objects.get_or_create(
        name=DEFAULT_LOCK_POLICY,
        defaults={"strategy": LineupStrategy.LOCK_BEFORE_FIRST_MATCH, "lock_minutes": 60},
    )
    return policy


# Valori di default delle fasi Worlds (configurabili dall'admin Django).
WORLDS_STAGE_DEFAULTS = [
    {
        "code": StageCode.PLAY_IN,
        "order": 1,
        "max_players_per_team": None,
        "free_transfers_unlimited_before": False,
        "budget_bonus": 0,
    },
    {
        "code": StageCode.SWISS,
        "order": 2,
        "max_players_per_team": 2,
        "free_transfers_unlimited_before": True,
        "budget_bonus": 0,
    },
    {
        "code": StageCode.QUARTERFINALS,
        "order": 3,
        "max_players_per_team": 3,
        "free_transfers_unlimited_before": True,
        "budget_bonus": 5,
    },
    {
        "code": StageCode.SEMIFINALS,
        "order": 4,
        "max_players_per_team": 4,
        "free_transfers_unlimited_before": True,
        "budget_bonus": 0,
    },
    {
        "code": StageCode.FINAL,
        "order": 5,
        "max_players_per_team": 5,
        "free_transfers_unlimited_before": True,
        "budget_bonus": 0,
    },
]


def ensure_worlds_stages(edition: CompetitionEdition) -> list[Stage]:
    stages = []
    for values in WORLDS_STAGE_DEFAULTS:
        defaults = {k: v for k, v in values.items() if k != "code"}
        stage, _ = Stage.objects.get_or_create(edition=edition, code=values["code"], defaults=defaults)
        stages.append(stage)
    return stages
