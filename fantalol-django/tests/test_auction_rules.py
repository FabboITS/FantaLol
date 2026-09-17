"""Porting di `league/AuctionServiceTest.java` e `LeagueAuctionPhaseServiceTest.java`."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.exceptions import BusinessRuleError
from leagues import services
from leagues.models import AuctionStatus, RosterEntry
from teams.models import PlayerRole

from .factories import (
    AdminFactory,
    FantaTeamFactory,
    LeagueFactory,
    ProPlayerFactory,
    RosterEntryFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def league_with_two_teams():
    admin = UserFactory()
    league = LeagueFactory(admin=admin, auction_open=True, participant_count=2)
    first = FantaTeamFactory(league=league, owner=admin, crediti_residui=1000)
    second = FantaTeamFactory(league=league, crediti_residui=1000)
    return league, first, second


def test_start_auction_requires_open_auction(league_with_two_teams):
    league, team, _ = league_with_two_teams
    league.auction_open = False
    league.save()
    player = ProPlayerFactory()
    with pytest.raises(BusinessRuleError, match="non è aperta"):
        services.start_auction(team.owner, league.id, player.id, team.id)


def test_start_auction_opens_at_player_quotation(league_with_two_teams):
    league, team, _ = league_with_two_teams
    player = ProPlayerFactory(quotazione=70)
    auction = services.start_auction(team.owner, league.id, player.id, team.id)
    assert auction.current_bid == 70
    assert auction.highest_bidder_id == team.id
    assert auction.status == AuctionStatus.ACTIVE


def test_only_one_active_auction_per_league(league_with_two_teams):
    league, team, _ = league_with_two_teams
    services.start_auction(team.owner, league.id, ProPlayerFactory().id, team.id)
    with pytest.raises(BusinessRuleError, match="già un'asta attiva"):
        services.start_auction(team.owner, league.id, ProPlayerFactory().id, team.id)


def test_player_already_in_league_cannot_be_auctioned(league_with_two_teams):
    league, team, other = league_with_two_teams
    player = ProPlayerFactory()
    RosterEntryFactory(fanta_team=other, player=player)
    with pytest.raises(BusinessRuleError, match="già assegnato"):
        services.start_auction(team.owner, league.id, player.id, team.id)


def test_bid_must_beat_current_bid(league_with_two_teams):
    league, team, other = league_with_two_teams
    auction = services.start_auction(team.owner, league.id, ProPlayerFactory(quotazione=50).id, team.id)
    with pytest.raises(BusinessRuleError, match="offerta minima è 51"):
        services.place_bid(other.owner, auction.id, other.id, 50)


def test_bid_resets_the_countdown(league_with_two_teams):
    league, team, other = league_with_two_teams
    auction = services.start_auction(team.owner, league.id, ProPlayerFactory(quotazione=50).id, team.id)
    auction.ends_at = timezone.now() + timedelta(seconds=1)
    auction.save()
    refreshed = services.place_bid(other.owner, auction.id, other.id, 60)
    assert refreshed.ends_at > timezone.now() + timedelta(seconds=10)
    assert refreshed.highest_bidder_id == other.id


def test_highest_bidder_cannot_outbid_itself(league_with_two_teams):
    league, team, _ = league_with_two_teams
    auction = services.start_auction(team.owner, league.id, ProPlayerFactory(quotazione=50).id, team.id)
    with pytest.raises(BusinessRuleError, match="già il miglior offerente"):
        services.place_bid(team.owner, auction.id, team.id, 100)


def test_bid_above_remaining_credits_is_rejected(league_with_two_teams):
    league, team, other = league_with_two_teams
    other.crediti_residui = 55
    other.save()
    auction = services.start_auction(team.owner, league.id, ProPlayerFactory(quotazione=50).id, team.id)
    with pytest.raises(BusinessRuleError, match="Crediti insufficienti"):
        services.place_bid(other.owner, auction.id, other.id, 60)


def test_expired_auction_assigns_player_and_charges_credits(league_with_two_teams):
    league, team, _ = league_with_two_teams
    player = ProPlayerFactory(quotazione=80)
    auction = services.start_auction(team.owner, league.id, player.id, team.id)
    auction.ends_at = timezone.now() - timedelta(seconds=1)
    auction.save()

    assert services.finalize_expired_auctions() == 1
    auction.refresh_from_db()
    team.refresh_from_db()
    assert auction.status == AuctionStatus.WON
    assert team.crediti_residui == 1000 - 80
    assert RosterEntry.objects.filter(fanta_team=team, player=player).exists()


def test_role_limit_blocks_the_auction(league_with_two_teams):
    league, team, _ = league_with_two_teams
    # Lega da 2 partecipanti: massimo 2 player per ruolo.
    for _ in range(2):
        RosterEntryFactory(fanta_team=team, player=ProPlayerFactory(ruolo=PlayerRole.MID))
    third = ProPlayerFactory(ruolo=PlayerRole.MID)
    with pytest.raises(BusinessRuleError, match="limite per il ruolo MID"):
        services.start_auction(team.owner, league.id, third.id, team.id)


def test_close_auction_requires_no_active_player_auction(league_with_two_teams):
    league, team, _ = league_with_two_teams
    services.start_auction(team.owner, league.id, ProPlayerFactory().id, team.id)
    with pytest.raises(BusinessRuleError, match="Attendi la fine"):
        services.close_auction(league.admin, league.id)


def test_open_auction_requires_started_competition():
    admin = UserFactory()
    league = LeagueFactory(admin=admin)
    with pytest.raises(BusinessRuleError, match="Crea una giornata"):
        services.open_auction(admin, league.id)


def test_only_league_creator_or_global_admin_manages_the_auction(league_with_two_teams):
    league, _, other = league_with_two_teams
    with pytest.raises(BusinessRuleError, match="Solo il creatore"):
        services.close_auction(other.owner, league.id)
    services.close_auction(AdminFactory(), league.id)
    league.refresh_from_db()
    assert league.auction_open is False
