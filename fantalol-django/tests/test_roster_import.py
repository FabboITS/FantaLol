"""Import dei roster pro da Leaguepedia, con Cargo API mockata."""
from io import StringIO

import httpx
import pytest
from django.core.management import CommandError, call_command

from teams.models import Competition, PlayerRole, ProPlayer, ProTeam

pytestmark = pytest.mark.django_db


def cargo_response(rows):
    return {"cargoquery": [{"title": row} for row in rows]}


LPL_TEAMS = [
    {"Name": "Bilibili Gaming", "Short": "BLG", "Region": "China",
     "Image": "BLG logo.png", "IsDisbanded": None},
    {"Name": "Top Esports", "Short": "TES", "Region": "China",
     "Image": "TES logo.png", "IsDisbanded": None},
    {"Name": "Royal Never Give Up", "Short": "RNG", "Region": "China",
     "Image": "RNG logo.png", "IsDisbanded": "Yes"},
]

BLG_PLAYERS = [
    {"ID": "Bin", "Player": "Chen Ze-Bin", "Country": "China", "Role": "Top",
     "Team": "Bilibili Gaming", "Image": "Bin.png", "IsRetired": None},
    {"ID": "Xun", "Player": "Peng Li-Xun", "Country": "China", "Role": "Jungle",
     "Team": "Bilibili Gaming", "Image": "Xun.png", "IsRetired": None},
    {"ID": "Knight", "Player": "Zhuo Ding", "Country": "China", "Role": "Mid",
     "Team": "Bilibili Gaming", "Image": "Knight.png", "IsRetired": None},
    {"ID": "Viper", "Player": "Park Do-hyeon", "Country": "South Korea", "Role": "Bot",
     "Team": "Bilibili Gaming", "Image": "Viper.png", "IsRetired": None},
    {"ID": "ON", "Player": "Luo Wen-Jun", "Country": "China", "Role": "Support",
     "Team": "Bilibili Gaming", "Image": "ON.png", "IsRetired": None},
    {"ID": "Allenatore", "Player": "Mister X", "Country": "China", "Role": "Coach",
     "Team": "Bilibili Gaming", "Image": None, "IsRetired": None},
    {"ID": "Veterano", "Player": "Mister Y", "Country": "China", "Role": "Mid",
     "Team": "Bilibili Gaming", "Image": None, "IsRetired": "Yes"},
]

TES_PLAYERS = [
    {"ID": "369", "Player": "Bai Jia-Hao", "Country": "China", "Role": "Top",
     "Team": "Top Esports", "Image": None, "IsRetired": None},
    {"ID": "Creme", "Player": "Lin Jian", "Country": "China", "Role": "Mid",
     "Team": "Top Esports", "Image": None, "IsRetired": None},
]


def transport_for(teams, players_by_team, *, fail_for=None):
    """Finto endpoint Cargo: risponde in base alla tabella richiesta."""
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        tables = params.get("tables", "")
        where = params.get("where", "")
        if tables.startswith("Teams"):
            return httpx.Response(200, json=cargo_response(teams))
        for name, rows in players_by_team.items():
            if f"'{name}'" in where:
                if fail_for == name:
                    return httpx.Response(500, json={"error": {"info": "boom"}})
                return httpx.Response(200, json=cargo_response(rows))
        return httpx.Response(200, json=cargo_response([]))

    return httpx.MockTransport(handler)


@pytest.fixture
def leaguepedia(monkeypatch):
    """Sostituisce il client con uno che parla al transport finto."""
    def install(teams, players_by_team, *, fail_for=None):
        from ingest.leaguepedia_client import LeaguepediaClient

        original_init = LeaguepediaClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("min_interval", 0)
            kwargs.setdefault("client", httpx.Client(
                transport=transport_for(teams, players_by_team, fail_for=fail_for),
                base_url="https://lol.test"))
            original_init(self, *args, **kwargs)

        monkeypatch.setattr(LeaguepediaClient, "__init__", patched_init)

    return install


def test_imports_teams_and_players_for_a_competition(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS})
    out = StringIO()
    call_command("import_rosters_leaguepedia", "--competition", "LPL", stdout=out)

    assert ProTeam.objects.filter(competition=Competition.LPL).count() == 2
    blg = ProTeam.objects.get(nome="Bilibili Gaming")
    assert blg.sigla == "BLG"
    assert blg.leaguepedia_name == "Bilibili Gaming"
    assert blg.competition == Competition.LPL

    roster = ProPlayer.objects.filter(team=blg).order_by("nickname")
    assert [p.nickname for p in roster] == ["Bin", "Knight", "ON", "Viper", "Xun"]
    viper = ProPlayer.objects.get(nickname="Viper")
    assert viper.ruolo == PlayerRole.ADC          # "Bot" -> ADC
    assert viper.nome_reale == "Park Do-hyeon"
    assert viper.nazionalita == "South Korea"
    assert viper.competition == Competition.LPL
    assert viper.leaguepedia_link == "Viper"


def test_skips_disbanded_teams_retired_players_and_staff(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS})
    call_command("import_rosters_leaguepedia", "--competition", "LPL", stdout=StringIO())

    assert not ProTeam.objects.filter(nome="Royal Never Give Up").exists()
    assert not ProPlayer.objects.filter(nickname="Veterano").exists()  # ritirato
    assert not ProPlayer.objects.filter(nickname="Allenatore").exists()  # ruolo Coach


def test_import_is_idempotent(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS})
    call_command("import_rosters_leaguepedia", "--competition", "LPL", stdout=StringIO())
    call_command("import_rosters_leaguepedia", "--competition", "LPL", stdout=StringIO())
    assert ProTeam.objects.count() == 2
    assert ProPlayer.objects.count() == 7


def test_dry_run_writes_nothing(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS})
    out = StringIO()
    call_command("import_rosters_leaguepedia", "--competition", "LPL", "--dry-run", stdout=out)
    assert ProTeam.objects.count() == 0
    assert ProPlayer.objects.count() == 0
    assert "NON importati" in out.getvalue()


def test_quotazione_is_configurable(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS})
    call_command("import_rosters_leaguepedia", "--competition", "LPL",
                 "--quotazione", "75", stdout=StringIO())
    assert {p.quotazione for p in ProPlayer.objects.all()} == {75}


def test_mark_worlds_flags_the_imported_players(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS})
    call_command("import_rosters_leaguepedia", "--competition", "LPL",
                 "--mark-worlds", stdout=StringIO())
    assert ProPlayer.objects.filter(is_worlds_eligible=True).count() == 7


def test_a_failing_team_does_not_abort_the_import(leaguepedia):
    leaguepedia(LPL_TEAMS, {"Bilibili Gaming": BLG_PLAYERS, "Top Esports": TES_PLAYERS},
                fail_for="Bilibili Gaming")
    err = StringIO()
    call_command("import_rosters_leaguepedia", "--competition", "LPL",
                 stdout=StringIO(), stderr=err)
    # Top Esports viene importata comunque.
    assert ProPlayer.objects.filter(team__nome="Top Esports").count() == 2
    assert "Bilibili Gaming" in err.getvalue()


def test_lck_uses_the_korean_region(leaguepedia):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if params.get("tables", "").startswith("Teams"):
            captured["where"] = params.get("where")
            return httpx.Response(200, json=cargo_response([
                {"Name": "T1", "Short": "T1", "Region": "Korea",
                 "Image": None, "IsDisbanded": None}]))
        return httpx.Response(200, json=cargo_response([
            {"ID": "Faker", "Player": "Lee Sang-hyeok", "Country": "South Korea",
             "Role": "Mid", "Team": "T1", "Image": None, "IsRetired": None}]))

    from ingest.leaguepedia_client import LeaguepediaClient

    original_init = LeaguepediaClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs.setdefault("min_interval", 0)
        kwargs.setdefault("client", httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://lol.test"))
        original_init(self, *args, **kwargs)

    LeaguepediaClient.__init__ = patched_init
    try:
        call_command("import_rosters_leaguepedia", "--competition", "LCK", stdout=StringIO())
    finally:
        LeaguepediaClient.__init__ = original_init

    assert captured["where"] == "T.Region='Korea'"
    faker = ProPlayer.objects.get(nickname="Faker")
    assert faker.competition == Competition.LCK
    assert faker.ruolo == PlayerRole.MID


def test_unknown_competition_is_rejected():
    with pytest.raises(CommandError, match="Competitivo sconosciuto"):
        call_command("import_rosters_leaguepedia", "--competition", "LFL", stdout=StringIO())


def test_no_teams_found_is_reported(leaguepedia):
    leaguepedia([], {})
    with pytest.raises(CommandError, match="Nessuna squadra trovata"):
        call_command("import_rosters_leaguepedia", "--competition", "LPL", stdout=StringIO())
