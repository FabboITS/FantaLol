"""Porting di `scoring/GameScoreCalculatorTest.java` e `matchday/FantaScoreCalculatorTest.java`.

Gli attesi numerici sono gli stessi del test JUnit: se un coefficiente cambia,
questi test devono rompersi.
"""
import pytest

from scoring.calculator import average_score, game_score, historical_score
from teams.models import PlayerRole


def test_applies_the_approved_summer_2026_weights_for_every_role():
    assert game_score(PlayerRole.TOP, 1, 1, 1, 100, 0, True) == 7.25
    assert game_score(PlayerRole.JUNGLE, 1, 1, 1, 100, 0, True) == 6.95
    assert game_score(PlayerRole.MID, 1, 1, 1, 100, 0, True) == 7.0
    assert game_score(PlayerRole.ADC, 1, 1, 1, 100, 0, True) == 6.85
    assert game_score(PlayerRole.SUPPORT, 1, 1, 1, 100, 50, True) == pytest.approx(6.95, abs=1e-4)


def test_scores_partial_hundreds_of_cs_continuously():
    assert game_score(PlayerRole.TOP, 0, 0, 0, 50, 999, False) == 0.625
    assert game_score(PlayerRole.ADC, 0, 0, 0, 125, 999, False) == 1.375


def test_scores_support_vision_continuously_and_ignores_support_cs():
    assert game_score(PlayerRole.SUPPORT, 0, 0, 0, 999, 0, False) == 0.0
    assert game_score(PlayerRole.SUPPORT, 0, 0, 0, 0, 25, False) == 0.5
    assert game_score(PlayerRole.SUPPORT, 0, 0, 0, 0, 50, False) == 1.0
    assert game_score(PlayerRole.SUPPORT, 0, 0, 0, 0, 100, False) == 2.0


def test_preserves_negative_scores():
    assert game_score(PlayerRole.SUPPORT, 0, 4, 0, 0, 0, False) == -7.0


def test_averages_aggregated_statistics_across_played_games():
    assert average_score(PlayerRole.MID, 4, 2, 8, 400, 0, 2, 2) == 17.0


def test_average_of_zero_games_is_zero():
    assert average_score(PlayerRole.MID, 4, 2, 8, 400, 0, 2, 0) == 0.0


def test_win_bonus_is_three_points():
    with_win = game_score(PlayerRole.MID, 0, 0, 0, 0, 0, True)
    without_win = game_score(PlayerRole.MID, 0, 0, 0, 0, 0, False)
    assert with_win - without_win == 3.0


def test_historical_formula_uses_integer_cs_buckets():
    # 3*3 + 2*2 - 2*2 + 1 + 3 = 13 (150 CS -> 1 punto, non 1.5)
    assert historical_score(3, 2, 2, 150, 1) == 13.0


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        game_score("JUNGLER", 1, 0, 0, 0, 0, False)
