"""Porting di `league/RosterPolicyTest.java`: dimensionamento rosa."""
import pytest

from .factories import FantaTeamFactory, LeagueFactory

pytestmark = pytest.mark.django_db


def test_six_teams_use_one_player_per_role():
    league = LeagueFactory()
    FantaTeamFactory.create_batch(6, league=league)
    assert league.roster_limits == (5, 1)


def test_five_teams_use_two_players_per_role():
    league = LeagueFactory()
    FantaTeamFactory.create_batch(5, league=league)
    assert league.roster_limits == (10, 2)


def test_frozen_participant_count_does_not_change_when_more_teams_are_counted():
    league = LeagueFactory(participant_count=5)
    FantaTeamFactory.create_batch(8, league=league)
    assert league.roster_limits == (10, 2)


def test_freeze_participant_count_is_idempotent():
    league = LeagueFactory()
    league.freeze_participant_count(4)
    league.freeze_participant_count(9)
    assert league.participant_count == 4


def test_fixed_roster_only_from_six_participants():
    assert LeagueFactory(participant_count=5).has_fixed_roster is False
    assert LeagueFactory(participant_count=6).has_fixed_roster is True
    assert LeagueFactory().has_fixed_roster is False
