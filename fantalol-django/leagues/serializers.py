"""Serializer leghe/rose/asta: chiavi JSON identiche ai DTO Spring."""
from __future__ import annotations

from rest_framework import serializers

from .models import AuctionSession, FantaTeam, League, RosterEntry


class LeagueRequestSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=100)
    creditiIniziali = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    competition = serializers.CharField(max_length=20, required=False, allow_null=True)


class LeagueResponseSerializer(serializers.ModelSerializer):
    codiceInvito = serializers.CharField(source="codice_invito", read_only=True)
    creditiIniziali = serializers.IntegerField(source="crediti_iniziali", read_only=True)
    adminUsername = serializers.CharField(source="admin.username", read_only=True)
    numeroSquadre = serializers.SerializerMethodField()
    auctionOpen = serializers.BooleanField(source="auction_open", read_only=True)
    participantCount = serializers.IntegerField(source="participant_count", read_only=True)
    competitionStarted = serializers.BooleanField(source="competition_started", read_only=True)
    maxRosterSize = serializers.SerializerMethodField()
    maxPerRole = serializers.SerializerMethodField()

    class Meta:
        model = League
        fields = [
            "id", "nome", "codiceInvito", "creditiIniziali", "adminUsername", "numeroSquadre",
            "auctionOpen", "participantCount", "competitionStarted", "maxRosterSize",
            "maxPerRole", "competition", "status",
        ]

    def get_numeroSquadre(self, league: League) -> int:
        return league.fanta_teams.count()

    def get_maxRosterSize(self, league: League) -> int:
        return league.roster_limits[0]

    def get_maxPerRole(self, league: League) -> int:
        return league.roster_limits[1]


class RosterEntryResponseSerializer(serializers.ModelSerializer):
    lecPlayerId = serializers.IntegerField(source="player_id", read_only=True)
    lecPlayerNickname = serializers.CharField(source="player.nickname", read_only=True)
    playerId = serializers.IntegerField(source="player_id", read_only=True)
    playerNickname = serializers.CharField(source="player.nickname", read_only=True)
    ruolo = serializers.CharField(source="player.ruolo", read_only=True)
    creditiSpesi = serializers.IntegerField(source="crediti_spesi", read_only=True)
    dataAcquisto = serializers.DateTimeField(source="data_acquisto", read_only=True)
    imageUrl = serializers.CharField(source="player.image_url", read_only=True)

    class Meta:
        model = RosterEntry
        fields = ["id", "lecPlayerId", "lecPlayerNickname", "playerId", "playerNickname",
                  "ruolo", "creditiSpesi", "dataAcquisto", "imageUrl"]


class FantaTeamResponseSerializer(serializers.ModelSerializer):
    creditiResidui = serializers.IntegerField(source="crediti_residui", read_only=True)
    leagueId = serializers.IntegerField(source="league_id", read_only=True)
    leagueNome = serializers.CharField(source="league.nome", read_only=True)
    ownerUsername = serializers.CharField(source="owner.username", read_only=True)
    rosa = RosterEntryResponseSerializer(many=True, read_only=True)

    class Meta:
        model = FantaTeam
        fields = ["id", "nome", "creditiResidui", "leagueId", "leagueNome", "ownerUsername",
                  "punti", "rosa"]


class JoinLeagueRequestSerializer(serializers.Serializer):
    codiceInvito = serializers.CharField(max_length=12)
    nomeSquadra = serializers.CharField(max_length=80)


class AcquistoPlayerRequestSerializer(serializers.Serializer):
    lecPlayerId = serializers.IntegerField(required=False)
    playerId = serializers.IntegerField(required=False)
    creditiOfferti = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if not attrs.get("lecPlayerId") and not attrs.get("playerId"):
            raise serializers.ValidationError("Il player è obbligatorio")
        attrs["playerId"] = attrs.get("playerId") or attrs.get("lecPlayerId")
        return attrs


class AuctionStartRequestSerializer(serializers.Serializer):
    leagueId = serializers.IntegerField()
    lecPlayerId = serializers.IntegerField(required=False)
    playerId = serializers.IntegerField(required=False)
    fantaTeamId = serializers.IntegerField()

    def validate(self, attrs):
        if not attrs.get("lecPlayerId") and not attrs.get("playerId"):
            raise serializers.ValidationError("Il player è obbligatorio")
        attrs["playerId"] = attrs.get("playerId") or attrs.get("lecPlayerId")
        return attrs


class AuctionBidRequestSerializer(serializers.Serializer):
    fantaTeamId = serializers.IntegerField()
    credits = serializers.IntegerField(min_value=1)


class AuctionResponseSerializer(serializers.ModelSerializer):
    leagueId = serializers.IntegerField(source="league_id", read_only=True)
    lecPlayerId = serializers.IntegerField(source="player_id", read_only=True)
    playerId = serializers.IntegerField(source="player_id", read_only=True)
    playerNickname = serializers.CharField(source="player.nickname", read_only=True)
    playerRole = serializers.CharField(source="player.ruolo", read_only=True)
    currentBid = serializers.IntegerField(source="current_bid", read_only=True)
    highestBidderId = serializers.IntegerField(source="highest_bidder_id", read_only=True)
    highestBidderName = serializers.SerializerMethodField()
    endsAt = serializers.DateTimeField(source="ends_at", read_only=True)

    class Meta:
        model = AuctionSession
        fields = ["id", "leagueId", "lecPlayerId", "playerId", "playerNickname", "playerRole",
                  "currentBid", "highestBidderId", "highestBidderName", "endsAt", "status"]

    def get_highestBidderName(self, auction: AuctionSession):
        return auction.highest_bidder.nome if auction.highest_bidder_id else None
