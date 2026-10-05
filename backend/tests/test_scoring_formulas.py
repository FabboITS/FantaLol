"""Porting di GameScoreCalculatorTest e FantaScoreCalculatorTest (stessi casi, tolleranza 1e-9)."""

import pytest

from apps.scoring import formulas

TOL = 1e-9


def test_applica_i_pesi_approvati_per_ogni_ruolo():
    assert formulas.game_score("TOP", 1, 1, 1, 100, 0, True) == pytest.approx(7.25, abs=TOL)
    assert formulas.game_score("JUNGLE", 1, 1, 1, 100, 0, True) == pytest.approx(6.95, abs=TOL)
    assert formulas.game_score("MID", 1, 1, 1, 100, 0, True) == pytest.approx(7.0, abs=TOL)
    assert formulas.game_score("ADC", 1, 1, 1, 100, 0, True) == pytest.approx(6.85, abs=TOL)
    assert formulas.game_score("SUPPORT", 1, 1, 1, 100, 50, True) == pytest.approx(6.95, abs=1e-4)


def test_cs_continui_a_frazioni_di_centinaio():
    assert formulas.game_score("TOP", 0, 0, 0, 50, 999, False) == pytest.approx(0.625, abs=TOL)
    assert formulas.game_score("ADC", 0, 0, 0, 125, 999, False) == pytest.approx(1.375, abs=TOL)


def test_vision_score_continuo_per_support_e_cs_ignorati():
    assert formulas.game_score("SUPPORT", 0, 0, 0, 999, 0, False) == 0
    assert formulas.game_score("SUPPORT", 0, 0, 0, 0, 25, False) == pytest.approx(0.5, abs=TOL)
    assert formulas.game_score("SUPPORT", 0, 0, 0, 0, 50, False) == pytest.approx(1.0, abs=TOL)
    assert formulas.game_score("SUPPORT", 0, 0, 0, 0, 100, False) == pytest.approx(2.0, abs=TOL)


def test_punteggi_negativi_conservati():
    assert formulas.game_score("SUPPORT", 0, 4, 0, 0, 0, False) == pytest.approx(-7.0, abs=TOL)


def test_media_di_statistiche_aggregate_sulle_partite_giocate():
    assert formulas.average_score("MID", 4, 2, 8, 400, 0, 2, 2) == pytest.approx(17.0, abs=TOL)
    assert formulas.average_score("MID", 4, 2, 8, 400, 0, 2, 0) == 0.0


def test_ruolo_obbligatorio():
    with pytest.raises(ValueError):
        formulas.weights_for(None)
    with pytest.raises(ValueError):
        formulas.weights_for("COACH")


# --- FantaScoreCalculatorTest (formula storica) -------------------------------------------------------
def test_storica_kill_assist_morti_centinaia_complete_di_cs_e_vittoria():
    assert formulas.historical_score(2, 1, 3, 250, 1) == 15.0


def test_storica_ammette_punteggi_negativi():
    assert formulas.historical_score(0, 4, 0, 99, 0) == -8.0


def test_storica_cs_solo_per_centinaia_complete():
    assert formulas.historical_score(0, 0, 0, 99, 0) == 0
    assert formulas.historical_score(0, 0, 0, 100, 0) == 1.0
    assert formulas.historical_score(0, 0, 0, 199, 0) == 1.0
    assert formulas.historical_score(0, 0, 0, 200, 0) == 2.0


def test_stat_score_usa_la_formula_versionata():
    kwargs = {
        "role": "SUPPORT",
        "kills": 1,
        "deaths": 1,
        "assists": 1,
        "cs": 100,
        "vision_score": 50,
        "wins": 1,
        "games_played": 1,
    }
    assert formulas.stat_score(formula_version="REGIONAL_V1", **kwargs) == pytest.approx(6.95, abs=1e-4)
    assert formulas.stat_score(formula_version="SUMMER_2026_V1", **kwargs) == pytest.approx(6.95, abs=1e-4)
    assert formulas.stat_score(formula_version="HISTORICAL", **kwargs) == 7.0


def test_serie_media_dei_game_giocati_e_giornata_somma_delle_serie():
    assert formulas.series_score([10.0, 20.0]) == 15.0
    assert formulas.series_score([]) == 0.0
    assert formulas.matchday_score([[10.0, 20.0], [6.0]]) == 21.0


def test_punteggio_regionale_media_dei_cinque_slot_con_zero_per_mancanti():
    assert formulas.regional_team_score([10, 10, 10, 10, None]) == 8.0
