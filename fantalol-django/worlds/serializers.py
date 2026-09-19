from rest_framework import serializers

from teams.serializers import ProTeamSummarySerializer

from .models import (
    WorldsAuctionSession,
    WorldsEdition,
    WorldsLeague,
    WorldsRosterEntry,
    WorldsStage,
    WorldsStageLineup,
    WorldsTeam,
)


class WorldsStageSerializer(serializers.ModelSerializer):
    startsAt = serializers.DateTimeField(source="starts_at", read_only=True)
    endsAt = serializers.DateTimeField(source="ends_at", read_only=True)
    lineupDeadline = serializers.SerializerMethodField()
    lineupsLocked = serializers.BooleanField(source="lineups_locked", read_only=True)
    advancementBonus = serializers.FloatField(source="advancement_bonus", read_only=True)

    class Meta:
        model = WorldsStage
        fields = ["id", "nome", "ordine", "startsAt", "endsAt", "lineupDeadline",
                  "lineupsLocked", "advancementBonus"]

    def get_lineupDeadline(self, stage: WorldsStage):
        return stage.effective_deadline()


class WorldsEditionSerializer(serializers.ModelSerializer):
    stages = WorldsStageSerializer(many=True, read_only=True)
    qualifiedTeams = ProTeamSummarySerializer(source="qualified_teams", many=True, read_only=True)
    defaultCrediti = serializers.IntegerField(source="default_crediti", read_only=True)
    defaultRosterSize = serializers.IntegerField(source="default_roster_size", read_only=True)
    defaultMaxPerRole = serializers.IntegerField(source="default_max_per_role", read_only=True)
    pandascoreTournamentId = serializers.IntegerField(source="pandascore_tournament_id", read_only=True)

    class Meta:
        model = WorldsEdition
        fields = ["id", "nome", "anno", "active", "pandascoreTournamentId", "defaultCrediti",
                  "defaultRosterSize", "defaultMaxPerRole", "stages", "qualifiedTeams"]


class WorldsEditionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorldsEdition
        fields = ["id", "nome", "anno", "active"]


class WorldsLeagueRequestSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=100)
    editionId = serializers.IntegerField()
    creditiIniziali = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    rosterSize = serializers.IntegerField(min_value=5, required=False, allow_null=True)
    maxPerRole = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    allowReentrySwap = serializers.BooleanField(required=False, default=True)
    mvpBonus = serializers.FloatField(required=False, default=3.0)
    seriesWinBonus = serializers.FloatField(required=False, default=1.0)


class WorldsLeagueResponseSerializer(serializers.ModelSerializer):
    codiceInvito = serializers.CharField(source="codice_invito", read_only=True)
    creditiIniziali = serializers.IntegerField(source="crediti_iniziali", read_only=True)
    rosterSize = serializers.IntegerField(source="roster_size", read_only=True)
    maxPerRole = serializers.IntegerField(source="max_per_role", read_only=True)
    auctionOpen = serializers.BooleanField(source="auction_open", read_only=True)
    allowReentrySwap = serializers.BooleanField(source="allow_reentry_swap", read_only=True)
    mvpBonus = serializers.FloatField(source="mvp_bonus", read_only=True)
    seriesWinBonus = serializers.FloatField(source="series_win_bonus", read_only=True)
    adminUsername = serializers.CharField(source="admin.username", read_only=True)
    edition = WorldsEditionSummarySerializer(read_only=True)
    numeroSquadre = serializers.SerializerMethodField()

    class Meta:
        model = WorldsLeague
        fields = ["id", "nome", "codiceInvito", "edition", "adminUsername", "creditiIniziali",
                  "rosterSize", "maxPerRole", "auctionOpen", "allowReentrySwap", "mvpBonus",
                  "seriesWinBonus", "numeroSquadre"]

    def get_numeroSquadre(self, league: WorldsLeague) -> int:
        return league.teams.count()


class WorldsRosterEntrySerializer(serializers.ModelSerializer):
    playerId = serializers.IntegerField(source="player_id", read_only=True)
    nickname = serializers.CharField(source="player.nickname", read_only=True)
    ruolo = serializers.CharField(source="player.ruolo", read_only=True)
    proTeam = serializers.CharField(source="player.team.nome", read_only=True)
    competition = serializers.CharField(source="player.competition", read_only=True)
    creditiSpesi = serializers.IntegerField(source="crediti_spesi", read_only=True)
    imageUrl = serializers.CharField(source="player.image_url", read_only=True)
    released = serializers.SerializerMethodField()

    class Meta:
        model = WorldsRosterEntry
        fields = ["id", "playerId", "nickname", "ruolo", "proTeam", "competition",
                  "creditiSpesi", "imageUrl", "released"]

    def get_released(self, entry: WorldsRosterEntry) -> bool:
        return entry.released_at_stage_id is not None


class WorldsTeamSerializer(serializers.ModelSerializer):
    leagueId = serializers.IntegerField(source="league_id", read_only=True)
    ownerUsername = serializers.CharField(source="owner.username", read_only=True)
    creditiResidui = serializers.IntegerField(source="crediti_residui", read_only=True)
    rosa = WorldsRosterEntrySerializer(many=True, read_only=True)

    class Meta:
        model = WorldsTeam
        fields = ["id", "nome", "leagueId", "ownerUsername", "creditiResidui", "rosa"]


class WorldsJoinRequestSerializer(serializers.Serializer):
    codiceInvito = serializers.CharField(max_length=12)
    nomeSquadra = serializers.CharField(max_length=80)


class WorldsLineupRequestSerializer(serializers.Serializer):
    stageId = serializers.IntegerField(required=False, allow_null=True)
    fantaTeamId = serializers.IntegerField()
    titolariIds = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class WorldsSwapRequestSerializer(serializers.Serializer):
    fantaTeamId = serializers.IntegerField()
    outPlayerId = serializers.IntegerField()
    inPlayerId = serializers.IntegerField()


class WorldsStageLineupSerializer(serializers.ModelSerializer):
    fantaTeamId = serializers.IntegerField(source="fanta_team_id", read_only=True)
    stageId = serializers.IntegerField(source="stage_id", read_only=True)
    stageNome = serializers.CharField(source="stage.nome", read_only=True)
    confirmedAt = serializers.DateTimeField(source="confirmed_at", read_only=True)
    titolari = serializers.SerializerMethodField()
    totale = serializers.FloatField(read_only=True)

    class Meta:
        model = WorldsStageLineup
        fields = ["id", "fantaTeamId", "stageId", "stageNome", "confirmed", "confirmedAt",
                  "titolari", "punteggio", "bonus", "totale"]

    def get_titolari(self, lineup: WorldsStageLineup):
        return [
            {"id": p.id, "nickname": p.nickname, "role": p.ruolo, "imageUrl": p.image_url}
            for p in lineup.titolari.all()
        ]


class WorldsAuctionSerializer(serializers.ModelSerializer):
    leagueId = serializers.IntegerField(source="league_id", read_only=True)
    playerId = serializers.IntegerField(source="player_id", read_only=True)
    playerNickname = serializers.CharField(source="player.nickname", read_only=True)
    playerRole = serializers.CharField(source="player.ruolo", read_only=True)
    currentBid = serializers.IntegerField(source="current_bid", read_only=True)
    highestBidderId = serializers.IntegerField(source="highest_bidder_id", read_only=True)
    highestBidderName = serializers.SerializerMethodField()
    endsAt = serializers.DateTimeField(source="ends_at", read_only=True)

    class Meta:
        model = WorldsAuctionSession
        fields = ["id", "leagueId", "playerId", "playerNickname", "playerRole", "currentBid",
                  "highestBidderId", "highestBidderName", "endsAt", "status"]

    def get_highestBidderName(self, auction: WorldsAuctionSession):
        return auction.highest_bidder.nome if auction.highest_bidder_id else None
