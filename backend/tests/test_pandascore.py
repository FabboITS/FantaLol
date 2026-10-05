"""PandaScore: client (solo endpoint di lista), worker di sync, roster, edizioni, fallimenti parziali."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from apps.competitions.models import Competition, CompetitionEdition, StageCode
from apps.esports.models import EditionRoster, EsportsMatch, ProPlayer, ProTeam, ProviderSyncState
from apps.providers.pandascore.client import PandaScoreClient, PandaScoreNotConfigured
from apps.providers.pandascore.worker import EsportsSyncWorker
from apps.worlds.stages import detect_stage_code

from .pipeline_helpers import PANDA, lck_edition, load, mock_lck, sync_lck

pytestmark = pytest.mark.django_db


def test_per_page_validato_lato_client():
    client = PandaScoreClient(token="t")
    for bad in (0, 101, "50"):
        with pytest.raises(ValueError):
            client.validate_per_page(bad)
    assert client.validate_per_page(100) == 100
    with pytest.raises(ValueError):
        client.league_matches(293, "finished")


def test_token_obbligatorio(settings):
    settings.PANDASCORE_API_TOKEN = None
    with pytest.raises(PandaScoreNotConfigured):
        PandaScoreClient()


@respx.mock
def test_parametri_e_header_degli_endpoint_di_lista():
    route = respx.get(f"{PANDA}/leagues/293/matches/past").mock(return_value=httpx.Response(
        200, json=[], headers={"Link": '<x>; rel="next"'}))
    page = PandaScoreClient().league_matches(293, "past", page=2, per_page=50)
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.url.params["sort"] == "-begin_at"
    assert request.url.params["filter[status]"] == "finished"
    assert request.url.params["per_page"] == "50"
    assert page.has_next
    upcoming = respx.get(f"{PANDA}/leagues/293/matches/upcoming").mock(
        return_value=httpx.Response(200, json=[{"id": 1}], headers={"X-Total": "120"}))
    page = PandaScoreClient().league_matches(293, "upcoming")
    assert upcoming.calls.last.request.url.params["sort"] == "begin_at"
    assert page.total == 120 and page.has_next


@respx.mock
def test_retry_con_backoff_su_errore_5xx():
    route = respx.get(f"{PANDA}/tournaments/1/rosters").mock(side_effect=[
        httpx.Response(502), httpx.Response(200, json={"rosters": [{"id": 1}]})])
    assert PandaScoreClient().tournament_rosters(1) == [{"id": 1}]
    assert route.call_count == 2


def test_worker_senza_token_non_parte_e_si_serve_la_cache(settings, caplog):
    settings.PANDASCORE_API_TOKEN = None
    assert EsportsSyncWorker().run() == {"skipped": True, "competitions": {}}
    assert "PANDASCORE_API_TOKEN assente" in caplog.text


def test_sync_lck_popola_team_match_risultati_e_roster():
    edition = sync_lck()
    assert ProTeam.objects.count() == 4
    gen = ProTeam.objects.get(pandascore_id=2882)
    assert gen.image_url_light.endswith("2882.png") and gen.image_url_dark.endswith("2882-dark.png")
    assert gen.logo_url == gen.image_url_light
    match = EsportsMatch.objects.get(pandascore_id=1100001)
    assert match.edition == edition and match.status == "finished" and match.winner_team == gen
    scores = {mt.team.acronym: (mt.score, mt.winner) for mt in match.match_teams.all()}
    assert scores == {"GEN": (2, True), "T1": (1, False)}
    assert not EsportsMatch.objects.filter(pandascore_id=1099999).exists()  # fuori finestra
    assert EsportsMatch.objects.get(pandascore_id=1100010).status == "not_started"
    assert EditionRoster.objects.filter(edition=edition).count() == 20  # il coach senza ruolo è escluso
    faker = ProPlayer.objects.get(nickname="Faker")
    assert faker.real_name == "Sang-hyeok Lee"
    assert EditionRoster.objects.get(player=faker).role == "MID"
    assert EditionRoster.objects.get(player__nickname="Canyon").role == "JUNGLE"
    state = ProviderSyncState.objects.get(provider="PANDASCORE", competition__code="LCK")
    assert state.status == "SUCCESS" and state.last_success_at


def test_quotazioni_admin_non_sovrascritte_e_cambio_squadra_chiude_il_periodo():
    edition = sync_lck()
    entry = EditionRoster.objects.get(edition=edition, player__nickname="Faker")
    entry.quotazione, entry.quotazione_set_by_admin = 42, True
    entry.save()
    rosters = load("pandascore/lck_rosters.json")
    faker = rosters["rosters"][1]["players"].pop(2)
    rosters["rosters"][2]["players"].append(faker)  # Faker passa a Nongshim
    with respx.mock(assert_all_called=False) as router:
        mock_lck(router)
        router.get(f"{PANDA}/tournaments/17001/rosters").mock(return_value=httpx.Response(200, json=rosters))
        EsportsSyncWorker().run("LCK")
    entries = EditionRoster.objects.filter(edition=edition, player__nickname="Faker").order_by("active_from")
    assert entries.count() == 2
    assert entries[0].active_to is not None
    assert entries[1].team.acronym == "NS" and entries[1].quotazione == 42 and entries[1].quotazione_set_by_admin


def test_fallimento_parziale_di_una_lega_non_blocca_le_altre():
    lck_edition()
    CompetitionEdition.objects.create(competition=Competition.objects.get(code="LEC"), year=2026, name="LEC",
                                      starts_at=datetime(2026, 7, 20, tzinfo=UTC), is_active=True)
    with respx.mock(assert_all_called=False) as router:
        mock_lck(router)
        router.get(url__regex=rf"{PANDA}/leagues/4197/.*").mock(return_value=httpx.Response(500))
        report = EsportsSyncWorker().run()
    assert "error" in report["competitions"]["LEC"]
    assert report["competitions"]["LCK"]["matches"] == 3
    assert ProviderSyncState.objects.get(competition__code="LEC", provider="PANDASCORE").status == "FAILED"
    assert ProviderSyncState.objects.get(competition__code="LCK", provider="PANDASCORE").status == "SUCCESS"


def test_errore_su_un_singolo_match_non_ferma_la_lega():
    lck_edition()
    broken = load("pandascore/lck_past.json")
    broken[1].pop("id")
    with respx.mock(assert_all_called=False) as router:
        mock_lck(router)
        router.get(f"{PANDA}/leagues/293/matches/past").mock(return_value=httpx.Response(200, json=broken))
        report = EsportsSyncWorker().run("LCK")
    assert report["competitions"]["LCK"]["errors"]
    assert EsportsMatch.objects.filter(pandascore_id=1100001).exists()


def test_scoperta_edizioni_dalle_serie_pandascore():
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{PANDA}/leagues/293/series").mock(return_value=httpx.Response(
            200, json=load("pandascore/lck_series.json")))
        editions = EsportsSyncWorker().discover_editions(Competition.objects.get(code="LCK"))
    assert len(editions) == 1
    edition = editions[0]
    assert edition.name == "LCK Rounds 3-5 2026" and edition.pandascore_tournament_ids == [17001]
    assert edition.get_lineup_policy().strategy == "LOCK_BEFORE_FIRST_MATCH"


def test_id_worlds_ricavato_dalla_ricerca_e_non_indovinato():
    worlds = Competition.objects.get(code="WORLDS")
    assert worlds.pandascore_league_id is None
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{PANDA}/lol/leagues").mock(return_value=httpx.Response(
            200, json=load("pandascore/worlds_leagues.json")))
        EsportsSyncWorker().resolve_league_id(worlds)
    worlds.refresh_from_db()
    assert worlds.pandascore_league_id == 297


@pytest.mark.parametrize(
    ("tournament", "match", "expected"),
    [
        ("Play-In", "PSG vs FLY", StageCode.PLAY_IN),
        ("Swiss Stage", "Round 1: GEN vs TL", StageCode.SWISS),
        ("Knockout Stage", "Quarterfinal 1: GEN vs HLE", StageCode.QUARTERFINALS),
        ("Playoffs", "Semifinal 2: T1 vs BLG", StageCode.SEMIFINALS),
        ("Knockout Stage", "Grand Final: GEN vs T1", StageCode.FINAL),
        ("Finals", "GEN vs T1", StageCode.FINAL),
        ("Showmatch", "All-Stars", None),
    ],
)
def test_riconoscimento_fasi_worlds(tournament, match, expected):
    assert detect_stage_code(tournament, match) == expected


def test_match_worlds_con_torneo_non_riconosciuto_ha_stage_nullo(caplog):
    edition = CompetitionEdition.objects.create(
        competition=Competition.objects.get(code="WORLDS"), year=2026, name="Worlds 2026",
        pandascore_serie_id=9500, starts_at=datetime(2026, 10, 1, tzinfo=UTC), is_active=True)
    raw = load("pandascore/lck_past.json")[0]
    raw.update({"serie_id": 9500, "tournament": {"id": 1, "name": "Showmatch"}, "name": "All-Stars"})
    match = EsportsSyncWorker(client=object()).upsert_match(raw, edition)
    assert match.stage is None
    assert "non riconosciuto" in caplog.text
    raw.update({"id": 777, "tournament": {"id": 2, "name": "Swiss Stage"}, "name": "GEN vs T1"})
    assert EsportsSyncWorker(client=object()).upsert_match(raw, edition).stage.code == "SWISS"
