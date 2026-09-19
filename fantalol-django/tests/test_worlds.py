"""Test della modalità Worlds: fasi, deadline formazione, swap, bonus, classifica."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.exceptions import BusinessRuleError
from ingest.models import Match, MatchStatus
from teams.models import ROLE_ORDER, Competition, PlayerRole
from worlds import bonuses, services
from worlds.models import WorldsRosterEntry, WorldsStageLineup

from .factories import (
    GameFactory,
    GamePlayerStatFactory,
    ProPlayerFactory,
    ProTeamFactory,
    WorldsEditionFactory,
    WorldsLeagueFactory,
    WorldsStageFactory,
    WorldsTeamFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def edition():
    edition = WorldsEditionFactory(nome="Worlds 2026", anno=2026)
    lec = ProTeamFactory(nome="G2 Esports", competition=Competition.LEC)
    lck = ProTeamFactory(nome="T1", competition=Competition.LCK)
    edition.qualified_teams.set([lec, lck])
    return edition


def roster_players(pro_team, prefix="P"):
    return [ProPlayerFactory(team=pro_team, ruolo=role.value, competition=pro_team.competition,
                             nickname=f"{prefix}-{role.value}")
            for role in ROLE_ORDER]


def stocked_team(edition, *, swap=True):
    league = WorldsLeagueFactory(edition=edition, allow_reentry_swap=swap,
                                 roster_size=10, max_per_role=2)
    team = WorldsTeamFactory(league=league, crediti_residui=500)
    pro_teams = list(edition.qualified_teams.all())
    players = roster_players(pro_teams[0], "A") + roster_players(pro_teams[1], "B")
    for player in players:
        WorldsRosterEntry.objects.create(fanta_team=team, player=player, crediti_spesi=20)
    return league, team, players


# --- player pool ----------------------------------------------------------
def test_worlds_pool_is_multi_region(edition):
    for pro_team in edition.qualified_teams.all():
        roster_players(pro_team, pro_team.nome)
    pool = services.worlds_player_pool(edition)
    competitions = set(pool.values_list("competition", flat=True))
    assert competitions == {Competition.LEC, Competition.LCK}
    assert pool.count() == 10


def test_mark_worlds_pool_sets_the_eligibility_flag(edition):
    for pro_team in edition.qualified_teams.all():
        roster_players(pro_team, pro_team.nome)
    assert services.mark_worlds_pool(edition) == 10
    assert all(services.worlds_player_pool(edition).values_list("is_worlds_eligible", flat=True))


def test_players_outside_the_pool_cannot_be_auctioned(edition):
    league, team, _ = stocked_team(edition)
    outsider = ProPlayerFactory(team=ProTeamFactory(nome="Squadra non qualificata"))
    with pytest.raises(BusinessRuleError, match="non fa parte del player pool"):
        services.assert_eligible(league, outsider)


# --- rosa e limiti --------------------------------------------------------
def test_roster_size_and_role_limits_come_from_the_league_config(edition):
    league, team, _ = stocked_team(edition)
    extra = ProPlayerFactory(team=edition.qualified_teams.first(), ruolo=PlayerRole.MID)
    with pytest.raises(BusinessRuleError, match="Rosa già completa"):
        services.validate_roster_slot(team, extra)

    league.roster_size = 12
    league.save()
    with pytest.raises(BusinessRuleError, match="limite per il ruolo MID"):
        services.validate_roster_slot(team, extra)


# --- formazione per fase --------------------------------------------------
def test_lineup_must_have_one_player_per_role(edition):
    league, team, players = stocked_team(edition)
    stage = WorldsStageFactory(edition=edition, nome="Swiss", ordine=1)
    duplicated = [p for p in players if p.ruolo == PlayerRole.MID][:2] + players[:3]
    with pytest.raises(BusinessRuleError):
        services.confirm_stage_lineup(team.owner, team.id, stage.id,
                                      [p.id for p in duplicated])


def test_lineup_is_confirmed_before_the_stage_deadline(edition):
    league, team, players = stocked_team(edition)
    deadline = timezone.now() + timedelta(hours=2)
    stage = WorldsStageFactory(edition=edition, ordine=1, lineup_deadline=deadline)
    titolari = [p for p in players if p.nickname.startswith("A-")]
    lineup = services.confirm_stage_lineup(team.owner, team.id, stage.id,
                                           [p.id for p in titolari])
    assert lineup.confirmed is True
    assert lineup.titolari.count() == 5


def test_lineup_is_rejected_after_the_stage_deadline(edition):
    league, team, players = stocked_team(edition)
    stage = WorldsStageFactory(edition=edition, ordine=1,
                               lineup_deadline=timezone.now() - timedelta(minutes=1))
    titolari = [p for p in players if p.nickname.startswith("A-")]
    with pytest.raises(BusinessRuleError, match="è chiusa"):
        services.confirm_stage_lineup(team.owner, team.id, stage.id, [p.id for p in titolari])


def test_deadline_defaults_to_the_first_match_of_the_stage(edition):
    stage = WorldsStageFactory(edition=edition, ordine=1, lineup_deadline=None)
    first = timezone.now() + timedelta(days=1)
    Match.objects.create(pandascore_id=1, league_code="WORLDS", status=MatchStatus.NOT_STARTED,
                         begin_at=first + timedelta(hours=3), worlds_stage=stage)
    Match.objects.create(pandascore_id=2, league_code="WORLDS", status=MatchStatus.NOT_STARTED,
                         begin_at=first, worlds_stage=stage)
    assert stage.effective_deadline() == first


def test_lock_due_stage_lineups_closes_expired_stages(edition):
    past = WorldsStageFactory(edition=edition, ordine=1,
                              lineup_deadline=timezone.now() - timedelta(hours=1))
    future = WorldsStageFactory(edition=edition, ordine=2,
                                lineup_deadline=timezone.now() + timedelta(hours=1))
    assert services.lock_due_stage_lineups() == 1
    past.refresh_from_db()
    future.refresh_from_db()
    assert past.lineups_locked is True
    assert future.lineups_locked is False


# --- sostituzioni fra fasi ------------------------------------------------
def test_free_swap_between_stages_charges_the_incoming_quotation(edition):
    league, team, players = stocked_team(edition, swap=True)
    WorldsStageFactory(edition=edition, ordine=1,
                       lineup_deadline=timezone.now() + timedelta(hours=5))
    outgoing = next(p for p in players if p.ruolo == PlayerRole.TOP)
    incoming = ProPlayerFactory(team=edition.qualified_teams.first(),
                                ruolo=PlayerRole.TOP, quotazione=40)

    services.swap_player(team.owner, team.id, outgoing.id, incoming.id)
    team.refresh_from_db()
    assert team.crediti_residui == 500 - 40
    current_ids = {entry.player_id for entry in services.active_roster(team)}
    assert incoming.id in current_ids and outgoing.id not in current_ids
    # Lo storico dell'ingaggio precedente resta, marcato come rilasciato.
    assert WorldsRosterEntry.objects.filter(fanta_team=team, player=outgoing).exists()


def test_swap_is_blocked_when_the_flag_is_off(edition):
    league, team, players = stocked_team(edition, swap=False)
    WorldsStageFactory(edition=edition, ordine=1,
                       lineup_deadline=timezone.now() + timedelta(hours=5))
    outgoing = next(p for p in players if p.ruolo == PlayerRole.TOP)
    incoming = ProPlayerFactory(team=edition.qualified_teams.first(), ruolo=PlayerRole.TOP)
    with pytest.raises(BusinessRuleError, match="non sono abilitate"):
        services.swap_player(team.owner, team.id, outgoing.id, incoming.id)


def test_swap_must_keep_the_same_role(edition):
    league, team, players = stocked_team(edition)
    WorldsStageFactory(edition=edition, ordine=1,
                       lineup_deadline=timezone.now() + timedelta(hours=5))
    outgoing = next(p for p in players if p.ruolo == PlayerRole.TOP)
    incoming = ProPlayerFactory(team=edition.qualified_teams.first(), ruolo=PlayerRole.ADC)
    with pytest.raises(BusinessRuleError, match="stesso ruolo"):
        services.swap_player(team.owner, team.id, outgoing.id, incoming.id)


def test_swap_is_blocked_after_the_stage_deadline(edition):
    league, team, players = stocked_team(edition)
    WorldsStageFactory(edition=edition, ordine=1,
                       lineup_deadline=timezone.now() - timedelta(minutes=5))
    outgoing = next(p for p in players if p.ruolo == PlayerRole.TOP)
    incoming = ProPlayerFactory(team=edition.qualified_teams.first(), ruolo=PlayerRole.TOP)
    with pytest.raises(BusinessRuleError, match="deadline"):
        services.swap_player(team.owner, team.id, outgoing.id, incoming.id)


# --- bonus ----------------------------------------------------------------
def test_mvp_bonus_counts_games_won_by_a_starter(edition):
    league, team, players = stocked_team(edition)
    stage = WorldsStageFactory(edition=edition, ordine=1)
    titolari = [p for p in players if p.nickname.startswith("A-")]
    match = Match.objects.create(pandascore_id=50, league_code="WORLDS",
                                 status=MatchStatus.FINISHED, begin_at=timezone.now(),
                                 worlds_stage=stage)
    GameFactory(match=match, mvp_player=titolari[0], external_game_id="W-G1")
    GameFactory(match=match, mvp_player=titolari[0], external_game_id="W-G2", game_number=2)
    assert bonuses.mvp_bonus(stage, titolari, amount=3.0) == 6.0
    assert bonuses.mvp_bonus(stage, titolari, amount=0.0) == 0.0


def test_series_win_bonus_counts_series_won_by_the_pro_team(edition):
    league, team, players = stocked_team(edition)
    stage = WorldsStageFactory(edition=edition, ordine=1)
    titolari = [p for p in players if p.nickname.startswith("A-")]
    pro_team_name = titolari[0].team.nome
    Match.objects.create(pandascore_id=60, league_code="WORLDS", status=MatchStatus.FINISHED,
                         begin_at=timezone.now(), worlds_stage=stage, winner_name=pro_team_name)
    Match.objects.create(pandascore_id=61, league_code="WORLDS", status=MatchStatus.FINISHED,
                         begin_at=timezone.now(), worlds_stage=stage, winner_name="Altra squadra")
    assert bonuses.series_win_bonus(stage, titolari, amount=1.0) == 1.0


def test_advancement_bonus_rewards_teams_present_in_the_next_stage(edition):
    league, team, players = stocked_team(edition)
    swiss = WorldsStageFactory(edition=edition, nome="Swiss", ordine=1)
    quarters = WorldsStageFactory(edition=edition, nome="Quarti", ordine=2)
    titolari = [p for p in players if p.nickname.startswith("A-")]
    Match.objects.create(pandascore_id=70, league_code="WORLDS", status=MatchStatus.NOT_STARTED,
                         begin_at=timezone.now(), worlds_stage=quarters,
                         opponents=[titolari[0].team.nome, "Altra"])
    # Cinque titolari della stessa squadra pro qualificata: 5 x 2.0
    assert bonuses.advancement_bonus(swiss, titolari, amount=2.0) == 10.0


def test_advancement_bonus_is_zero_on_the_final_stage(edition):
    league, team, players = stocked_team(edition)
    final = WorldsStageFactory(edition=edition, nome="Finale", ordine=9)
    titolari = [p for p in players if p.nickname.startswith("A-")]
    assert bonuses.advancement_bonus(final, titolari, amount=2.0) == 0.0


# --- punteggi e classifica ------------------------------------------------
def test_stage_score_sums_the_fantasy_points_of_the_starters(edition):
    league, team, players = stocked_team(edition)
    stage = WorldsStageFactory(edition=edition, ordine=1,
                               lineup_deadline=timezone.now() + timedelta(hours=1))
    titolari = [p for p in players if p.nickname.startswith("A-")]
    match = Match.objects.create(pandascore_id=80, league_code="WORLDS",
                                 status=MatchStatus.FINISHED, begin_at=timezone.now(),
                                 worlds_stage=stage)
    game = GameFactory(match=match, external_game_id="W-S1")
    for player in titolari:
        stat = GamePlayerStatFactory(game=game, player=player, role=player.ruolo)
        stat.fantasy_score = 6.0
        stat.save()

    lineup = services.confirm_stage_lineup(team.owner, team.id, stage.id,
                                           [p.id for p in titolari])
    assert lineup.punteggio == pytest.approx(30.0)


def test_standings_are_cumulative_across_stages_and_break_ties_by_bonus(edition):
    league = WorldsLeagueFactory(edition=edition, mvp_bonus=0.0, series_win_bonus=0.0)
    stage = WorldsStageFactory(edition=edition, ordine=1, advancement_bonus=0.0)
    first = WorldsTeamFactory(league=league, nome="Alfa")
    second = WorldsTeamFactory(league=league, nome="Beta")
    WorldsStageLineup.objects.create(fanta_team=first, stage=stage, punteggio=10.0, bonus=0.0)
    WorldsStageLineup.objects.create(fanta_team=second, stage=stage, punteggio=6.0, bonus=4.0)

    rows = services.standings(league)
    # Stesso totale (10): vince chi ha più bonus.
    assert [row["teamNome"] for row in rows] == ["Beta", "Alfa"]
    assert rows[0]["posizione"] == 1
    assert rows[0]["totale"] == pytest.approx(10.0)


def test_standings_list_every_stage_even_without_a_lineup(edition):
    league = WorldsLeagueFactory(edition=edition)
    WorldsStageFactory(edition=edition, nome="Swiss", ordine=1)
    WorldsStageFactory(edition=edition, nome="Quarti", ordine=2)
    WorldsTeamFactory(league=league, nome="Solo")
    row = services.standings(league)[0]
    assert [stage["stageNome"] for stage in row["stages"]] == ["Swiss", "Quarti"]
    assert all(stage["confirmed"] is False for stage in row["stages"])
    assert row["totale"] == 0.0
