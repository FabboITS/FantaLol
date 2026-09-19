"""Porting di `CumulativeScoringServiceTest`: media cumulativa e titolare storico."""
from datetime import timedelta

import pytest
from django.utils import timezone

from lineups.models import LineupPeriod
from scoring import services
from teams.models import ROLE_ORDER, PlayerRole

from .factories import (
    FantaTeamFactory,
    GameFactory,
    GamePlayerStatFactory,
    LeagueFactory,
    ProPlayerFactory,
)

pytestmark = pytest.mark.django_db


def stat_for(player, *, played_at, score, **kwargs):
    game = GameFactory(played_at=played_at)
    stat = GamePlayerStatFactory(game=game, player=player, role=player.ruolo, **kwargs)
    stat.fantasy_score = score
    stat.save()
    return stat


def test_player_score_is_the_average_over_played_games():
    player = ProPlayerFactory(ruolo=PlayerRole.MID)
    now = timezone.now()
    stat_for(player, played_at=now - timedelta(days=3), score=10.0)
    stat_for(player, played_at=now - timedelta(days=2), score=20.0)
    score = services.player_score(player.id)
    assert score["gamesPlayed"] == 2
    assert score["average"] == pytest.approx(15.0)


def test_non_participating_stats_are_excluded():
    player = ProPlayerFactory(ruolo=PlayerRole.MID)
    now = timezone.now()
    stat_for(player, played_at=now - timedelta(days=3), score=10.0)
    stat_for(player, played_at=now - timedelta(days=2), score=100.0,
             corrected_participated=False)
    assert services.player_score(player.id)["average"] == pytest.approx(10.0)


def test_team_score_uses_the_historical_starter_of_each_slot():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    now = timezone.now()
    switch = now - timedelta(days=7)

    old_mid = ProPlayerFactory(ruolo=PlayerRole.MID)
    new_mid = ProPlayerFactory(ruolo=PlayerRole.MID)
    LineupPeriod.objects.create(fanta_team=team, role=PlayerRole.MID, player=old_mid,
                                valid_from=switch - timedelta(days=20), valid_to=switch)
    LineupPeriod.objects.create(fanta_team=team, role=PlayerRole.MID, player=new_mid,
                                valid_from=switch)
    # Gli altri quattro slot restano coperti, così il punteggio non è provvisorio.
    for role in ROLE_ORDER:
        if role == PlayerRole.MID:
            continue
        player = ProPlayerFactory(ruolo=role.value)
        LineupPeriod.objects.create(fanta_team=team, role=role.value, player=player,
                                    valid_from=switch - timedelta(days=20))
        stat_for(player, played_at=now - timedelta(days=1), score=4.0)

    # Il game giocato prima del cambio conta per il vecchio titolare...
    stat_for(old_mid, played_at=switch - timedelta(days=1), score=30.0)
    # ...quello dopo il cambio per il nuovo.
    stat_for(new_mid, played_at=switch + timedelta(days=1), score=10.0)
    # Un game del vecchio MID dopo l'uscita non deve più contare.
    stat_for(old_mid, played_at=now - timedelta(hours=1), score=999.0)

    score = services.team_score(team.id)
    mid_slot = next(slot for slot in score["slots"] if slot["role"] == PlayerRole.MID)
    assert mid_slot["gamesPlayed"] == 2
    assert mid_slot["average"] == pytest.approx(20.0)
    assert sorted(mid_slot["contributingPlayers"]) == sorted([old_mid.nickname, new_mid.nickname])
    assert score["provisional"] is False
    assert score["overallTotal"] == pytest.approx(30.0 + 10.0 + 4 * 4.0)


def test_team_score_is_provisional_while_a_slot_has_no_data():
    league = LeagueFactory(participant_count=2)
    team = FantaTeamFactory(league=league)
    player = ProPlayerFactory(ruolo=PlayerRole.TOP)
    LineupPeriod.objects.create(fanta_team=team, role=PlayerRole.TOP, player=player,
                                valid_from=timezone.now() - timedelta(days=30))
    stat_for(player, played_at=timezone.now() - timedelta(days=1), score=8.0)

    score = services.team_score(team.id)
    assert score["provisional"] is True
    assert score["overallTotal"] is None
    awaiting = [slot for slot in score["slots"] if slot["status"] == "awaiting-data"]
    assert len(awaiting) == 4


def test_league_ranking_sorts_by_total_then_name():
    league = LeagueFactory(participant_count=2)
    first = FantaTeamFactory(league=league, nome="Alfa")
    second = FantaTeamFactory(league=league, nome="Beta")
    now = timezone.now()
    for team, score in ((first, 2.0), (second, 5.0)):
        for role in ROLE_ORDER:
            player = ProPlayerFactory(ruolo=role.value)
            LineupPeriod.objects.create(fanta_team=team, role=role.value, player=player,
                                        valid_from=now - timedelta(days=30))
            stat_for(player, played_at=now - timedelta(days=1), score=score)

    ranking = services.league_ranking(league.id)
    assert [row["teamName"] for row in ranking] == ["Beta", "Alfa"]


def test_envelope_includes_leaguepedia_attribution():
    payload = services.player_scores_response()
    assert "Leaguepedia" in payload["attribution"]
    assert "CC BY-SA" in payload["attribution"]


def test_recompute_applies_manual_corrections():
    player = ProPlayerFactory(ruolo=PlayerRole.MID)
    game = GameFactory()
    stat = GamePlayerStatFactory(game=game, player=player, role=PlayerRole.MID,
                                 kills=1, deaths=0, assists=0, cs=0, win=False)
    services.recompute_scores_for_game(game)
    stat.refresh_from_db()
    assert stat.fantasy_score == pytest.approx(3.0)

    stat.corrected_kills = 3
    stat.save()
    services.recompute_scores_for_game(game)
    stat.refresh_from_db()
    assert stat.fantasy_score == pytest.approx(9.0)
