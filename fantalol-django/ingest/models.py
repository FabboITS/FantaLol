"""Modelli della pipeline di ingest PandaScore + Leaguepedia.

Sostituiscono `integration/oracle/ProviderGame` e `ProviderPlayerGameStat`:
il calendario e lo stato delle serie arrivano da PandaScore, i box score per
game da Leaguepedia (Cargo API). Nessun CSV manuale.
"""
from __future__ import annotations

from django.db import models

from teams.models import PlayerRole, ProPlayer, ProTeam


class SyncStatus(models.TextChoices):
    OK = "OK", "OK"
    PARTIAL = "PARTIAL", "PARTIAL"
    ERROR = "ERROR", "ERROR"
    SKIPPED = "SKIPPED", "SKIPPED"


class SyncState(models.Model):
    """Stato dell'ultimo ciclo di sync per provider (ex `esports_sync_state`).

    Il fallimento parziale è normale: un errore su una lega non interrompe il
    ciclo, viene solo registrato qui.
    """

    provider = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.OK)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    last_success_at = models.DateTimeField(blank=True, null=True)
    last_error = models.CharField(max_length=1000, blank=True, null=True)
    inserted = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ingest_sync_states"

    def __str__(self) -> str:
        return f"{self.provider}: {self.status}"


class TeamAlias(models.Model):
    """Mapping nome PandaScore -> nome canonico Leaguepedia.

    I mismatch di nome sono **dati, non codice**: si gestiscono da Django admin,
    mai con costanti hardcoded nei client.
    """

    source_name = models.CharField(max_length=160, unique=True)
    canonical_name = models.CharField(max_length=160)
    team = models.ForeignKey(ProTeam, on_delete=models.SET_NULL, blank=True, null=True,
                             related_name="aliases")

    class Meta:
        db_table = "ingest_team_aliases"
        ordering = ["source_name"]

    def __str__(self) -> str:
        return f"{self.source_name} -> {self.canonical_name}"


class PlayerAlias(models.Model):
    """Mapping nome/Link esterno -> `ProPlayer` interno."""

    source_name = models.CharField(max_length=160, unique=True)
    canonical_name = models.CharField(max_length=160)
    player = models.ForeignKey(ProPlayer, on_delete=models.SET_NULL, blank=True, null=True,
                               related_name="aliases")

    class Meta:
        db_table = "ingest_player_aliases"
        ordering = ["source_name"]

    def __str__(self) -> str:
        return f"{self.source_name} -> {self.canonical_name}"


class MatchStatus(models.TextChoices):
    NOT_STARTED = "not_started", "not_started"
    RUNNING = "running", "running"
    FINISHED = "finished", "finished"
    CANCELED = "canceled", "canceled"
    POSTPONED = "postponed", "postponed"


class Match(models.Model):
    """Serie (best-of-N) importata da PandaScore."""

    pandascore_id = models.BigIntegerField(unique=True)
    slug = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=250, blank=True, null=True)
    league_code = models.CharField(max_length=20, db_index=True)
    league_pandascore_id = models.BigIntegerField(blank=True, null=True)
    tournament_name = models.CharField(max_length=200, blank=True, null=True)
    serie_name = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=MatchStatus.choices,
                              default=MatchStatus.NOT_STARTED, db_index=True)
    begin_at = models.DateTimeField(blank=True, null=True, db_index=True)
    end_at = models.DateTimeField(blank=True, null=True)
    number_of_games = models.IntegerField(default=0)
    opponents = models.JSONField(default=list, blank=True)
    results = models.JSONField(default=list, blank=True)
    winner_name = models.CharField(max_length=160, blank=True, null=True)
    #: Edizione Worlds a cui la serie appartiene (solo modalità Worlds).
    worlds_stage = models.ForeignKey("worlds.WorldsStage", on_delete=models.SET_NULL,
                                     blank=True, null=True, related_name="matches")
    #: Tracciamento dell'enrich Leaguepedia.
    leaguepedia_checked_at = models.DateTimeField(blank=True, null=True)
    leaguepedia_synced_at = models.DateTimeField(blank=True, null=True)
    leaguepedia_attempts = models.IntegerField(default=0)
    leaguepedia_error = models.CharField(max_length=1000, blank=True, null=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ingest_matches"
        ordering = ["-begin_at"]
        indexes = [
            # Indice equivalente a quello parziale Postgres della pipeline
            # sorgente: serve a pescare in coda le serie finite da arricchire.
            models.Index(fields=["status", "leaguepedia_synced_at", "leaguepedia_checked_at"],
                         name="idx_match_enrich_queue"),
            models.Index(fields=["league_code", "begin_at"], name="idx_match_league_begin"),
        ]

    def __str__(self) -> str:
        return self.name or f"match {self.pandascore_id}"

    @property
    def needs_enrichment(self) -> bool:
        return self.status == MatchStatus.FINISHED and self.leaguepedia_synced_at is None


class Game(models.Model):
    """Singolo game di una serie, con i dati identificativi Leaguepedia."""

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="games")
    game_number = models.IntegerField(default=1)
    #: `GameId` di Leaguepedia: chiave naturale per l'idempotenza dell'import.
    external_game_id = models.CharField(max_length=200, db_index=True)
    played_at = models.DateTimeField(db_index=True)
    duration_seconds = models.IntegerField(blank=True, null=True)
    patch = models.CharField(max_length=20, blank=True, null=True)
    winner_name = models.CharField(max_length=160, blank=True, null=True)
    #: MVP della serie/game secondo Leaguepedia, usato dai bonus Worlds.
    mvp_link = models.CharField(max_length=160, blank=True, null=True)
    mvp_player = models.ForeignKey(ProPlayer, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name="mvp_games")

    class Meta:
        db_table = "ingest_games"
        ordering = ["played_at", "game_number"]
        constraints = [
            # Import idempotente: mai due volte lo stesso game.
            models.UniqueConstraint(fields=["external_game_id"], name="uq_game_external_id"),
            models.UniqueConstraint(fields=["match", "game_number"], name="uq_game_match_number"),
        ]

    def __str__(self) -> str:
        return self.external_game_id


class GamePlayerStat(models.Model):
    """Box score di un player in un game (`ScoreboardPlayers` di Leaguepedia)."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="player_stats")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="game_stats")
    #: Chiave `Link` di Leaguepedia, conservata anche quando l'alias cambia.
    source_link = models.CharField(max_length=160)
    source_team_name = models.CharField(max_length=160, blank=True, null=True)
    role = models.CharField(max_length=20, choices=PlayerRole.choices)
    champion = models.CharField(max_length=80, blank=True, null=True)
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    cs = models.IntegerField(default=0)
    gold = models.IntegerField(default=0)
    damage = models.IntegerField(default=0)
    vision_score = models.IntegerField(default=0)
    win = models.BooleanField(default=False)
    #: Fantapunti calcolati con la formula per-ruolo di `scoring`.
    fantasy_score = models.FloatField(default=0.0)
    #: Correzioni manuali dell'ADMIN: prevalgono sui dati grezzi.
    corrected_kills = models.IntegerField(blank=True, null=True)
    corrected_deaths = models.IntegerField(blank=True, null=True)
    corrected_assists = models.IntegerField(blank=True, null=True)
    corrected_cs = models.IntegerField(blank=True, null=True)
    corrected_vision_score = models.IntegerField(blank=True, null=True)
    corrected_win = models.BooleanField(blank=True, null=True)
    corrected_participated = models.BooleanField(blank=True, null=True)
    overridden = models.BooleanField(default=False)
    override_actor = models.CharField(max_length=120, blank=True, null=True)
    overridden_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "ingest_game_player_stats"
        constraints = [
            models.UniqueConstraint(fields=["game", "player"], name="uq_game_player_stat"),
        ]
        indexes = [models.Index(fields=["player", "game"])]

    def __str__(self) -> str:
        return f"{self.player_id}@{self.game_id}"

    # --- valori effettivi (grezzi o corretti) ------------------------------
    @property
    def effective_kills(self) -> int:
        return self.kills if self.corrected_kills is None else self.corrected_kills

    @property
    def effective_deaths(self) -> int:
        return self.deaths if self.corrected_deaths is None else self.corrected_deaths

    @property
    def effective_assists(self) -> int:
        return self.assists if self.corrected_assists is None else self.corrected_assists

    @property
    def effective_cs(self) -> int:
        return self.cs if self.corrected_cs is None else self.corrected_cs

    @property
    def effective_vision_score(self) -> int:
        return self.vision_score if self.corrected_vision_score is None else self.corrected_vision_score

    @property
    def effective_win(self) -> bool:
        return self.win if self.corrected_win is None else self.corrected_win

    @property
    def participated(self) -> bool:
        return True if self.corrected_participated is None else self.corrected_participated

    def recompute_fantasy_score(self) -> float:
        from scoring.calculator import game_score

        self.fantasy_score = game_score(
            self.role,
            self.effective_kills,
            self.effective_deaths,
            self.effective_assists,
            self.effective_cs,
            self.effective_vision_score,
            self.effective_win,
        )
        return self.fantasy_score
