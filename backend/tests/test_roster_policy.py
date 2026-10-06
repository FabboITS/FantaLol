"""Porting di RosterPolicyTest + generalizzazione T=10 / T=14 / T=16."""

import pytest

from apps.leagues import policy
from apps.leagues.policy import Limits

from .factories import EditionFactory, FantaTeamFactory, LeagueFactory, build_edition_rosters, competition


@pytest.mark.parametrize(
    ("teams", "participants", "expected"),
    [
        (10, 2, Limits(10, 2)),
        (10, 5, Limits(10, 2)),
        (10, 6, Limits(5, 1)),
        (10, 10, Limits(5, 1)),
        (14, 7, Limits(10, 2)),
        (14, 8, Limits(5, 1)),
        (14, 14, Limits(5, 1)),
        (16, 8, Limits(10, 2)),
        (16, 9, Limits(5, 1)),
    ],
)
def test_limiti_parametrici(teams, participants, expected):
    assert policy.limits_for(participants, teams) == expected


@pytest.mark.django_db
def test_sei_squadre_usano_un_player_per_ruolo():
    league = LeagueFactory()
    build_edition_rosters(league.edition, 10)
    for _ in range(6):
        FantaTeamFactory(league=league)
    assert policy.roster_limits(league) == Limits(5, 1)


@pytest.mark.django_db
def test_cinque_squadre_usano_due_player_per_ruolo():
    league = LeagueFactory()
    build_edition_rosters(league.edition, 10)
    for _ in range(5):
        FantaTeamFactory(league=league)
    assert policy.roster_limits(league) == Limits(10, 2)


@pytest.mark.django_db
def test_partecipanti_congelati_non_cambiano_con_altre_squadre():
    league = LeagueFactory(participant_count=5)
    build_edition_rosters(league.edition, 10)
    for _ in range(7):
        FantaTeamFactory(league=league)
    assert policy.roster_limits(league) == Limits(10, 2)


@pytest.mark.django_db
def test_lpl_con_quattordici_team():
    edition = EditionFactory(competition=competition("LPL"))
    build_edition_rosters(edition, 14)
    league = LeagueFactory(edition=edition, participant_count=7)
    assert policy.edition_team_count(edition) == 14
    assert policy.max_participants(league) == 14
    assert policy.roster_limits(league) == Limits(10, 2)
    assert not policy.is_fixed_roster(league)
    league.participant_count = 8
    assert policy.is_fixed_roster(league)
    assert policy.fixed_roster_threshold(league) == 8


@pytest.mark.django_db
def test_worlds_rosa_da_otto_senza_limite_per_ruolo():
    edition = EditionFactory(competition=competition("WORLDS"))
    league = LeagueFactory(edition=edition, settings={"max_participants": 50})
    assert policy.roster_limits(league) == Limits(8, None)
    assert policy.max_participants(league) == 50
    assert not policy.is_fixed_roster(league)


@pytest.mark.django_db
def test_edizione_senza_roster_usa_dieci_team_di_default():
    assert policy.edition_team_count(EditionFactory()) == 10
