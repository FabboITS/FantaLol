"""Dati reali (team, player, roster, serie, game, statistiche) condivisi da tutte le leghe."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from apps.common.utils import PlayerRole
from apps.competitions.models import Competition, CompetitionEdition, Stage


class ProTeam(models.Model):
    pandascore_id = models.BigIntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=120)
    acronym = models.CharField(max_length=20, blank=True, default="")
    slug = models.SlugField(max_length=140, blank=True, default="")
    location = models.CharField(max_length=60, blank=True, default="")
    image_url_light = models.CharField(max_length=500, blank=True, default="")
    image_url_dark = models.CharField(max_length=500, blank=True, default="")
    logo_file = models.CharField(max_length=255, blank=True, default="")
    logo_hash = models.CharField(max_length=64, blank=True, default="")
    logo_etag = models.CharField(max_length=200, blank=True, default="")
    leaguepedia_name = models.CharField(max_length=120, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pro_teams"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def logo_url(self) -> str | None:
        if self.logo_file:
            return f"/media/{self.logo_file}"
        return self.image_url_light or self.image_url_dark or None


class ProPlayer(models.Model):
    pandascore_id = models.BigIntegerField(unique=True, null=True, blank=True)
    leaguepedia_link = models.CharField(max_length=160, unique=True, null=True, blank=True)
    nickname = models.CharField(max_length=60)
    real_name = models.CharField(max_length=120, blank=True, default="")
    nationality = models.CharField(max_length=60, blank=True, default="")
    image_url = models.CharField(max_length=500, blank=True, default="")
    image_file = models.CharField(max_length=255, blank=True, default="")
    image_hash = models.CharField(max_length=64, blank=True, default="")
    image_etag = models.CharField(max_length=200, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pro_players"
        ordering = ["nickname"]

    def __str__(self) -> str:
        return self.nickname

    @property
    def photo_url(self) -> str | None:
        if self.image_file:
            return f"/media/{self.image_file}"
        return self.image_url or None


class EditionRoster(models.Model):
    """Appartenenza di un player a un team in una edizione (con quotazione dell'edizione)."""

    edition = models.ForeignKey(CompetitionEdition, on_delete=models.CASCADE, related_name="rosters")
    team = models.ForeignKey(ProTeam, on_delete=models.CASCADE, related_name="edition_rosters")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="edition_rosters")
    role = models.CharField(max_length=10, choices=PlayerRole.choices)
    quotazione = models.PositiveIntegerField(default=1)
    quotazione_set_by_admin = models.BooleanField(default=False)
    is_starter = models.BooleanField(default=True)
    in_listone = models.BooleanField(null=True, blank=True)
    active_from = models.DateTimeField()
    active_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "edition_rosters"
        ordering = ["edition_id", "team__name", "role"]
        constraints = [
            models.UniqueConstraint(fields=["edition", "player", "active_from"], name="uniq_roster_period")
        ]
        indexes = [models.Index(fields=["edition", "active_to"], name="idx_roster_active")]

    def __str__(self) -> str:
        return f"{self.player} @ {self.team} ({self.edition})"


class MatchStatus(models.TextChoices):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELED = "canceled"
    POSTPONED = "postponed"


class EsportsMatch(models.Model):
    pandascore_id = models.BigIntegerField(unique=True)
    edition = models.ForeignKey(
        CompetitionEdition, on_delete=models.CASCADE, related_name="matches", null=True, blank=True
    )
    stage = models.ForeignKey(Stage, on_delete=models.SET_NULL, null=True, blank=True, related_name="matches")
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=MatchStatus.choices, default=MatchStatus.NOT_STARTED)
    begin_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    number_of_games = models.PositiveSmallIntegerField(default=1)
    winner_team = models.ForeignKey(
        ProTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    pandascore_tournament_id = models.BigIntegerField(null=True, blank=True)
    pandascore_serie_id = models.BigIntegerField(null=True, blank=True)
    tournament_name = models.CharField(max_length=120, blank=True, default="")
    leaguepedia_synced_at = models.DateTimeField(null=True, blank=True)
    leaguepedia_checked_at = models.DateTimeField(null=True, blank=True)
    stats_complete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "esports_matches"
        ordering = ["begin_at", "id"]
        indexes = [
            models.Index(
                F("leaguepedia_checked_at").asc(nulls_first=True),
                F("end_at").desc(),
                name="idx_match_enrich_queue",
                condition=Q(status="finished", leaguepedia_synced_at__isnull=True),
            ),
            models.Index(fields=["edition", "begin_at"], name="idx_match_edition_begin"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def competition(self) -> Competition | None:
        return self.edition.competition if self.edition_id else None


class EsportsMatchTeam(models.Model):
    match = models.ForeignKey(EsportsMatch, on_delete=models.CASCADE, related_name="match_teams")
    team = models.ForeignKey(ProTeam, on_delete=models.CASCADE, related_name="match_entries")
    position = models.PositiveSmallIntegerField(default=1)
    score = models.PositiveSmallIntegerField(default=0)
    winner = models.BooleanField(default=False)

    class Meta:
        db_table = "esports_match_teams"
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["match", "team"], name="uniq_match_team")]


class EsportsGame(models.Model):
    match = models.ForeignKey(EsportsMatch, on_delete=models.CASCADE, related_name="games")
    game_number = models.PositiveSmallIntegerField()
    leaguepedia_game_id = models.CharField(max_length=200, unique=True, null=True, blank=True)
    winner_team = models.ForeignKey(
        ProTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    length_seconds = models.PositiveIntegerField(null=True, blank=True)
    played_at = models.DateTimeField(null=True, blank=True)
    mvp_link = models.CharField(max_length=160, blank=True, default="")
    overview_page = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "esports_games"
        ordering = ["match_id", "game_number"]
        constraints = [models.UniqueConstraint(fields=["match", "game_number"], name="uniq_game_number")]


class StatSource(models.TextChoices):
    LEAGUEPEDIA = "LEAGUEPEDIA"
    MANUAL = "MANUAL"


class GamePlayerStat(models.Model):
    game = models.ForeignKey(EsportsGame, on_delete=models.CASCADE, related_name="player_stats")
    player = models.ForeignKey(
        ProPlayer, on_delete=models.SET_NULL, null=True, blank=True, related_name="game_stats"
    )
    leaguepedia_link = models.CharField(max_length=160)
    source_team_name = models.CharField(max_length=120, blank=True, default="")
    team = models.ForeignKey(ProTeam, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    side = models.CharField(max_length=10, blank=True, default="")
    role = models.CharField(max_length=10, blank=True, default="")
    champion = models.CharField(max_length=60, blank=True, default="")
    kills = models.IntegerField(null=True, blank=True)
    deaths = models.IntegerField(null=True, blank=True)
    assists = models.IntegerField(null=True, blank=True)
    gold = models.IntegerField(null=True, blank=True)
    cs = models.IntegerField(null=True, blank=True)
    damage_to_champions = models.IntegerField(null=True, blank=True)
    vision_score = models.IntegerField(null=True, blank=True)
    win = models.BooleanField(null=True, blank=True)
    is_complete = models.BooleanField(default=True)
    source = models.CharField(max_length=16, choices=StatSource.choices, default=StatSource.LEAGUEPEDIA)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "game_player_stats"
        ordering = ["game_id", "id"]
        constraints = [
            models.UniqueConstraint(fields=["game", "leaguepedia_link"], name="uniq_game_player_link")
        ]
        indexes = [models.Index(fields=["player"], name="idx_stat_player")]


class GamePlayerStatOverride(models.Model):
    """Correzione manuale dell'admin (riproduce ``PlayerGameCorrectionService``)."""

    game = models.ForeignKey(EsportsGame, on_delete=models.CASCADE, related_name="overrides")
    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="stat_overrides")
    participated = models.BooleanField(null=True, blank=True)
    kills = models.IntegerField(null=True, blank=True)
    deaths = models.IntegerField(null=True, blank=True)
    assists = models.IntegerField(null=True, blank=True)
    cs = models.IntegerField(null=True, blank=True)
    vision_score = models.IntegerField(null=True, blank=True)
    win = models.BooleanField(null=True, blank=True)
    champion = models.CharField(max_length=60, blank=True, default="")
    actor = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "game_player_stat_overrides"
        constraints = [models.UniqueConstraint(fields=["game", "player"], name="uniq_override_game_player")]


class TeamAlias(models.Model):
    """Nome PandaScore → nome Leaguepedia (le discrepanze sono dati, non codice)."""

    team = models.ForeignKey(ProTeam, on_delete=models.CASCADE, null=True, blank=True, related_name="aliases")
    pandascore_name = models.CharField(max_length=120, unique=True)
    leaguepedia_name = models.CharField(max_length=120)

    class Meta:
        db_table = "team_aliases"

    def __str__(self) -> str:
        return f"{self.pandascore_name} → {self.leaguepedia_name}"


class PlayerAlias(models.Model):
    """``Link`` Leaguepedia → player."""

    player = models.ForeignKey(ProPlayer, on_delete=models.CASCADE, related_name="aliases")
    leaguepedia_link = models.CharField(max_length=160, unique=True)

    class Meta:
        db_table = "player_aliases"

    def __str__(self) -> str:
        return f"{self.leaguepedia_link} → {self.player}"


class Provider(models.TextChoices):
    PANDASCORE = "PANDASCORE"
    LEAGUEPEDIA = "LEAGUEPEDIA"


class ProviderSyncState(models.Model):
    provider = models.CharField(max_length=20, choices=Provider.choices)
    competition = models.ForeignKey(
        Competition, on_delete=models.CASCADE, null=True, blank=True, related_name="sync_states"
    )
    status = models.CharField(max_length=20, default="AWAITING_DATA")
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=1000, blank=True, default="")
    sync_requested_at = models.DateTimeField(null=True, blank=True)
    inserted_games = models.PositiveIntegerField(default=0)
    updated_games = models.PositiveIntegerField(default=0)
    skipped_games = models.PositiveIntegerField(default=0)
    failed_games = models.PositiveIntegerField(default=0)
    unmatched_players = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "provider_sync_states"
        constraints = [
            models.UniqueConstraint(fields=["provider", "competition"], name="uniq_provider_competition"),
            models.UniqueConstraint(
                fields=["provider"], condition=Q(competition__isnull=True), name="uniq_provider_global"
            ),
        ]
