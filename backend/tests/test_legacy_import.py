"""Migrazione dal database MySQL del backend Java (import idempotente)."""

import bcrypt
import pytest

from apps.leagues.models import FantaTeam, League, RosterEntry
from apps.lineups.models import EffectiveLineupPeriod
from apps.matchdays.models import Formation, PlayerStat
from apps.users.legacy_import import import_rows
from apps.users.models import User
from apps.users.services import login

pytestmark = pytest.mark.django_db


def legacy_rows():
    hashed = bcrypt.hashpw(b"segreta1", bcrypt.gensalt(rounds=4)).decode().replace("$2b$", "$2a$", 1)
    return {
        "users": [
            {
                "id": 1,
                "username": "mago",
                "email": "mago@x.it",
                "password": hashed,
                "role": "USER",
                "enabled": 1,
            },
            {"id": 2, "username": "Natsu_Admin", "email": "a@x.it", "password": hashed, "role": "ADMIN"},
        ],
        "user_profiles": [{"user_id": 1, "nome_visualizzato": "Il Mago"}],
        "lec_teams": [
            {"id": 10, "nome": "G2 Esports", "sigla": "G2", "logo_url": "/assets/team-logos/g2.png"}
        ],
        "lec_players": [
            {"id": 100, "nickname": "Caps", "ruolo": "MID", "quotazione": 100, "team_id": 10},
            {"id": 101, "nickname": "BrokenBlade", "ruolo": "TOP", "quotazione": 90, "team_id": 10},
        ],
        "leagues": [
            {
                "id": 5,
                "nome": "Lega storica",
                "codice_invito": "ABCD1234",
                "crediti_iniziali": 1000,
                "admin_id": 1,
                "auction_open": 0,
                "participant_count": 2,
            }
        ],
        "fanta_teams": [
            {"id": 50, "nome": "Blue", "crediti_residui": 810, "league_id": 5, "owner_id": 1, "punti": 12.5}
        ],
        "roster_entries": [{"fanta_team_id": 50, "lec_player_id": 100, "crediti_spesi": 190}],
        "matchdays": [{"id": 7, "numero": 1, "league_id": 5, "chiusa": 1, "status": "CLOSED"}],
        "player_stats": [
            {
                "matchday_id": 7,
                "lec_player_id": 100,
                "kills": 3,
                "morti": 1,
                "assist": 4,
                "cs": 250,
                "vittoria": 1,
                "fantavoto": 15.0,
                "formula_version": None,
            }
        ],
        "formations": [
            {
                "id": 70,
                "fanta_team_id": 50,
                "matchday_id": 7,
                "source": "SUBMITTED",
                "confirmed": 1,
                "punteggio_totale": 3.0,
            }
        ],
        "formation_titolari": [{"formation_id": 70, "lec_player_id": 100}],
        "effective_lineup_periods": [
            {
                "fanta_team_id": 50,
                "role": "MID",
                "lec_player_id": 100,
                "effective_from": "2026-07-23T22:00:00Z",
                "origin": "BACKFILL",
            }
        ],
    }


def test_import_completo_e_idempotente():
    report = import_rows(legacy_rows())
    assert report["users_created"] == 2 and report["roster_entries"] == 1
    assert login("mago", "segreta1")["role"] == "USER"
    assert User.objects.get(username="Natsu_Admin").role == "ADMIN"
    league = League.objects.get(codice_invito="ABCD1234")
    assert league.edition.name == "LEC 2026 Summer" and league.participant_count == 2
    team = FantaTeam.objects.get()
    assert team.crediti_residui == 810 and team.punti == 12.5
    stat = PlayerStat.objects.get()
    assert stat.formula_version == "HISTORICAL" and stat.fantavoto == 15.0 and stat.wins == 1
    assert Formation.objects.get().titolari.count() == 1
    assert EffectiveLineupPeriod.objects.count() == 1
    again = import_rows(legacy_rows())
    assert again["users_existing"] == 2 and "roster_entries" not in again
    assert RosterEntry.objects.count() == 1 and User.objects.count() == 2
