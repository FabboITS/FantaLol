"""Porting di `FantaTeamServiceTest`, `LeagueRosterCompletionTest`,
`EffectiveLineupServiceTest` e `FormationServiceTest`."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from core.exceptions import BusinessRuleError
from leagues import services as league_services
from leagues.models import RosterEntry
from lineups import services as lineup_services
from lineups.models import LineupPeriod
from matchdays import services as matchday_services
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
FRIDAY = datetime(2026, 7, 31, 12, 0, tzinfo=ROME)


def five_players(team=None, **kwargs):
    team = team or ProTeamFactory()
    return [ProPlayerFactory(team=team, ruolo=role.value, **kwargs) for role in ROLE_ORDER]


def roster_of_five(fanta_team):
    players = five_players()
    for player in players:
        RosterEntryFactory(fanta_team=fanta_team, player=player)
    return players


# --- acquisto -------------------------------------------------------------
def test_join_league_creates_team_with_initial_credits():
    league = LeagueFactory(crediti_iniziali=800)
    user = UserFactory()
    team = league_services.join_league(user, league.codice_invito, "I miei")
    assert team.crediti_residui == 800
    assert team.league_id == league.id


def test_cannot_join_twice_the_same_league():
    league = LeagueFactory()
    user = UserFactory()
    league_services.join_league(user, league.codice_invito, "Primo")
    with pytest.raises(BusinessRuleError, match="già iscritto"):
        league_services.join_league(user, league.codice_invito, "Secondo")


def test_cannot_join_a_started_league():
    league = LeagueFactory(participant_count=4)
    with pytest.raises(BusinessRuleError, match="già iniziata"):
        league_services.join_league(UserFactory(), league.codice_invito, "Tardi")


def test_acquisto_below_quotation_is_rejected():
    team = FantaTeamFactory()
    player = ProPlayerFactory(quotazione=90)
    with pytest.raises(BusinessRuleError, match="inferiore alla quotazione"):
        league_services.acquista_player(team.owner, team.id, player.id, 80)


def test_acquisto_above_remaining_credits_is_rejected():
    team = FantaTeamFactory(crediti_residui=40)
    player = ProPlayerFactory(quotazione=10)
    with pytest.raises(BusinessRuleError, match="Crediti insufficienti"):
        league_services.acquista_player(team.owner, team.id, player.id, 60)


def test_acquisto_charges_credits_and_creates_roster_entry():
    team = FantaTeamFactory(crediti_residui=500)
    player = ProPlayerFactory(quotazione=60)
    entry = league_services.acquista_player(team.owner, team.id, player.id, 75)
    team.refresh_from_db()
    assert entry.crediti_spesi == 75
    assert team.crediti_residui == 425


def test_same_player_cannot_be_in_two_teams_of_the_same_league():
    league = LeagueFactory(participant_count=2)
    first = FantaTeamFactory(league=league)
    second = FantaTeamFactory(league=league)
    player = ProPlayerFactory(quotazione=10)
    league_services.acquista_player(first.owner, first.id, player.id, 10)
    with pytest.raises(BusinessRuleError, match="già stato acquistato"):
        league_services.acquista_player(second.owner, second.id, player.id, 10)


def test_release_refunds_half_the_credits():
    team = FantaTeamFactory(crediti_residui=500)
    entry = RosterEntryFactory(fanta_team=team, crediti_spesi=81)
    league_services.rilascia_player(team.owner, team.id, entry.id)
    team.refresh_from_db()
    assert team.crediti_residui == 500 + 40  # 81 // 2
    assert not RosterEntry.objects.filter(pk=entry.pk).exists()


def test_complete_all_rosters_randomly_fills_every_role():
    league = LeagueFactory(participant_count=6)
    teams = [FantaTeamFactory(league=league) for _ in range(6)]
    for _ in range(8):
        five_players()
    league_services.complete_all_rosters_randomly(league.admin, league.id)
    for team in teams:
        roles = sorted(entry.player.ruolo for entry in team.rosa.select_related("player"))
        assert roles == sorted(role.value for role in ROLE_ORDER)


def test_complete_all_rosters_requires_closed_auction():
    league = LeagueFactory(participant_count=2, auction_open=True)
    FantaTeamFactory(league=league)
    with pytest.raises(BusinessRuleError, match="Termina l'asta"):
        league_services.complete_all_rosters_randomly(league.admin, league.id)


def test_complete_all_rosters_fails_when_pool_is_too_small():
    league = LeagueFactory(participant_count=6)
    for _ in range(6):
        FantaTeamFactory(league=league)
    five_players()  # un solo player per ruolo per sei squadre
    with pytest.raises(BusinessRuleError, match="abbastanza player"):
        league_services.complete_all_rosters_randomly(league.admin, league.id)


# --- storico formazioni ---------------------------------------------------
def test_schedule_requires_one_player_per_role():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    duplicated = players[:4] + [ProPlayerFactory(ruolo=PlayerRole.MID)]
    with pytest.raises(BusinessRuleError, match="un player per ruolo"):
        lineup_services.schedule(team.owner, team.id, duplicated, now=WEDNESDAY)


def test_schedule_is_rejected_outside_the_window():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    with pytest.raises(BusinessRuleError, match="da martedì a giovedì"):
        lineup_services.schedule(team.owner, team.id, players, now=FRIDAY)


def test_schedule_is_rejected_for_fixed_roster_leagues():
    league = LeagueFactory(participant_count=8)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    with pytest.raises(BusinessRuleError, match="almeno 6 squadre"):
        lineup_services.schedule(team.owner, team.id, players, now=WEDNESDAY)


def test_schedule_opens_periods_from_the_next_friday():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    lineup_services.schedule(team.owner, team.id, players, now=WEDNESDAY)
    periods = LineupPeriod.objects.filter(fanta_team=team)
    assert periods.count() == 5
    assert all(p.valid_from == datetime(2026, 7, 31, tzinfo=ROME) for p in periods)
    assert all(p.valid_to is None for p in periods)


def test_rescheduling_closes_the_previous_period_without_rewriting_history():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    lineup_services.schedule(team.owner, team.id, players, now=WEDNESDAY)
    LineupPeriod.objects.filter(fanta_team=team).update(
        valid_from=datetime(2026, 7, 24, tzinfo=ROME))

    substitute = ProPlayerFactory(ruolo=PlayerRole.MID)
    RosterEntryFactory(fanta_team=team, player=substitute)
    new_lineup = [p for p in players if p.ruolo != PlayerRole.MID] + [substitute]
    lineup_services.schedule(team.owner, team.id, new_lineup, now=WEDNESDAY)

    mid_periods = LineupPeriod.objects.filter(fanta_team=team, role=PlayerRole.MID).order_by("valid_from")
    assert mid_periods.count() == 2
    # Il periodo storico resta, chiuso al venerdì successivo.
    assert mid_periods[0].valid_to == datetime(2026, 7, 31, tzinfo=ROME)
    assert mid_periods[1].player_id == substitute.id
    assert mid_periods[1].valid_to is None


def test_active_players_at_returns_the_historical_starter():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    old, new = ProPlayerFactory(ruolo=PlayerRole.TOP), ProPlayerFactory(ruolo=PlayerRole.TOP)
    switch = timezone.now() - timedelta(days=7)
    LineupPeriod.objects.create(fanta_team=team, role=PlayerRole.TOP, player=old,
                                valid_from=switch - timedelta(days=14), valid_to=switch)
    LineupPeriod.objects.create(fanta_team=team, role=PlayerRole.TOP, player=new,
                                valid_from=switch)
    assert lineup_services.active_players_at(team.id, switch - timedelta(days=1)) == {old.id}
    assert lineup_services.active_players_at(team.id, switch + timedelta(days=1)) == {new.id}


# --- formazione per giornata ---------------------------------------------
def test_schedule_lineup_requires_players_from_the_roster():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    roster_of_five(team)
    outsider = ProPlayerFactory(ruolo=PlayerRole.TOP)
    ids = [p.id for p in five_players()[:4]] + [outsider.id]
    with pytest.raises(BusinessRuleError, match="non appartiene alla rosa"):
        matchday_services.schedule_lineup(team.owner, team.id, ids, now=WEDNESDAY)


def test_schedule_lineup_requires_exactly_five_players():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    with pytest.raises(BusinessRuleError, match="esattamente 5 titolari"):
        matchday_services.schedule_lineup(team.owner, team.id, [p.id for p in players[:4]],
                                          now=WEDNESDAY)


def test_schedule_lineup_is_blocked_while_the_auction_is_open():
    league = LeagueFactory(participant_count=2, auction_open=True)
    team = FantaTeamFactory(league=league)
    players = roster_of_five(team)
    with pytest.raises(BusinessRuleError, match="Termina l'asta"):
        matchday_services.schedule_lineup(team.owner, team.id, [p.id for p in players],
                                          now=WEDNESDAY)
