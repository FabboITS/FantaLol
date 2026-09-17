"""Porting di `MatchdayLifecycleServiceTest`, `MatchdayScoringServiceTest`,
`FormationControllerTest` e `FormationAdminController`."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from core.exceptions import BusinessRuleError
from matchdays import services
from matchdays.models import Formation, FormationSource, Matchday, MatchdayStatus, PlayerStat
from teams.models import ROLE_ORDER, PlayerRole

from .factories import (
    FantaTeamFactory,
    LeagueFactory,
    ProPlayerFactory,
    ProTeamFactory,
    RosterEntryFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db
ROME = ZoneInfo("Europe/Rome")
WEDNESDAY = datetime(2026, 7, 29, 12, 0, tzinfo=ROME)


def league_with_team(participants=2, owner=None):
    admin = UserFactory()
    league = LeagueFactory(admin=admin)
    teams = [FantaTeamFactory(league=league,
                              owner=owner if (owner and i == 0) else UserFactory())
             for i in range(participants)]
    return league, teams


def fill_roster(team):
    pro_team = ProTeamFactory()
    players = [ProPlayerFactory(team=pro_team, ruolo=role.value) for role in ROLE_ORDER]
    for player in players:
        RosterEntryFactory(fanta_team=team, player=player)
    return players


# --- ciclo di vita giornata ----------------------------------------------
def test_first_matchday_starts_the_competition_and_freezes_participants():
    league, teams = league_with_team(3)
    matchday = services.create_matchday(league.admin, league.id, 1, "Prima", date(2026, 8, 1))
    league.refresh_from_db()
    assert matchday.numero == 1
    assert league.participant_count == 3
    assert league.auction_open is True


def test_competition_requires_at_least_two_teams():
    league, _ = league_with_team(1)
    with pytest.raises(BusinessRuleError, match="almeno 2 squadre"):
        services.create_matchday(league.admin, league.id, 1, None, None)


def test_matchday_numbers_are_unique_per_league():
    league, _ = league_with_team(2)
    services.create_matchday(league.admin, league.id, 1, None, None)
    with pytest.raises(BusinessRuleError, match="esiste già"):
        services.create_matchday(league.admin, league.id, 1, None, None)


def test_only_the_league_admin_creates_matchdays():
    league, teams = league_with_team(2)
    with pytest.raises(BusinessRuleError, match="Solo il creatore"):
        services.create_matchday(teams[1].owner, league.id, 1, None, None)


def test_waiting_for_postponed_is_rejected_once_closed():
    league, _ = league_with_team(2)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    services.close_matchday(league.admin, matchday.id)
    with pytest.raises(BusinessRuleError, match="già chiusa"):
        services.mark_waiting_for_postponed(league.admin, matchday.id)


def test_marking_waiting_for_postponed_keeps_the_matchday_open():
    league, _ = league_with_team(2)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    updated = services.mark_waiting_for_postponed(league.admin, matchday.id)
    assert updated.status == MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES
    assert updated.chiusa is False


def test_closing_a_matchday_scores_the_confirmed_formations():
    league, teams = league_with_team(2)
    team = teams[0]
    players = fill_roster(team)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)

    formation = Formation.objects.create(fanta_team=team, matchday=matchday, confirmed=True)
    formation.titolari.set(players)
    for player, voto in zip(players, [5.0, 3.0, 2.0, 1.0, -1.0]):
        stat = PlayerStat.objects.create(matchday=matchday, player=player, fantavoto=voto)
        assert stat.fantavoto == voto

    services.close_matchday(league.admin, matchday.id)
    formation.refresh_from_db()
    matchday.refresh_from_db()
    assert matchday.status == MatchdayStatus.CLOSED
    assert formation.punteggio_totale == pytest.approx(10.0)


# --- statistiche ----------------------------------------------------------
def test_player_stat_recompute_uses_the_role_formula():
    player = ProPlayerFactory(ruolo=PlayerRole.SUPPORT)
    league, _ = league_with_team(2)
    matchday = Matchday.objects.create(league=league, numero=7)
    stat = PlayerStat.objects.create(matchday=matchday, player=player, kills=2, morti=1,
                                     assist=10, vision_score=100, wins=1, games_played=1)
    # SUPPORT: 4.30 + 25.50 - 1.75 + 2.00 + 3.00 = 33.05
    assert stat.recompute() == pytest.approx(33.05)


# --- conferma formazione --------------------------------------------------
def test_confirm_formation_records_the_starters_and_opens_the_history():
    owner = UserFactory()
    league, teams = league_with_team(2, owner=owner)
    team = teams[0]
    players = fill_roster(team)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)

    formation = services.confirm_formation(owner, team.id, matchday.id,
                                           [p.id for p in players], now=WEDNESDAY)
    assert formation.confirmed is True
    assert formation.source == FormationSource.SUBMITTED
    assert formation.titolari.count() == 5
    assert team.lineup_periods.count() == 5


def test_confirm_formation_rejects_a_closed_matchday():
    owner = UserFactory()
    league, teams = league_with_team(2, owner=owner)
    team = teams[0]
    players = fill_roster(team)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    services.close_matchday(league.admin, matchday.id)
    with pytest.raises(BusinessRuleError, match="già chiusa"):
        services.confirm_formation(owner, team.id, matchday.id, [p.id for p in players],
                                   now=WEDNESDAY)


def test_confirm_formation_rejects_a_matchday_of_another_league():
    owner = UserFactory()
    league, teams = league_with_team(2, owner=owner)
    other_league, _ = league_with_team(2)
    other_matchday = services.create_matchday(other_league.admin, other_league.id, 1, None, None)
    players = fill_roster(teams[0])
    with pytest.raises(BusinessRuleError, match="non appartiene alla lega"):
        services.confirm_formation(owner, teams[0].id, other_matchday.id,
                                   [p.id for p in players], now=WEDNESDAY)


def test_fixed_roster_leagues_confirm_the_whole_roster():
    owner = UserFactory()
    league, teams = league_with_team(6, owner=owner)
    team = teams[0]
    players = fill_roster(team)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    formation = services.confirm_formation(owner, team.id, matchday.id, [], now=WEDNESDAY)
    assert sorted(p.id for p in formation.titolari.all()) == sorted(p.id for p in players)


def test_confirm_all_formations_fills_the_missing_ones():
    league, teams = league_with_team(2)
    for team in teams:
        fill_roster(team)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    payloads = services.confirm_all_formations(league.admin, league.id, matchday.id)
    assert len(payloads) == 2
    assert all(payload["source"] == FormationSource.AUTOMATIC for payload in payloads)
    assert all(payload["confirmed"] for payload in payloads)


def test_confirm_all_formations_marks_incomplete_rosters_as_missing():
    league, teams = league_with_team(2)
    RosterEntryFactory(fanta_team=teams[0])
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    payloads = services.confirm_all_formations(league.admin, league.id, matchday.id)
    assert all(payload["source"] == FormationSource.MISSING for payload in payloads)


def test_formation_history_reports_the_matchday_scores():
    owner = UserFactory()
    league, teams = league_with_team(2, owner=owner)
    team = teams[0]
    players = fill_roster(team)
    matchday = services.create_matchday(league.admin, league.id, 1, None, None)
    services.confirm_formation(owner, team.id, matchday.id, [p.id for p in players],
                               now=WEDNESDAY)
    PlayerStat.objects.create(matchday=matchday, player=players[0], fantavoto=9.5)

    history = services.formation_history(owner, team.id)
    assert len(history) == 1
    scores = {row["id"]: row["matchdayScore"] for row in history[0]["players"]}
    assert scores[players[0].id] == pytest.approx(9.5)
