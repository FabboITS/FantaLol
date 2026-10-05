"""Porting di EffectiveLineupServiceTest, LineupBackfillServiceTest e FormationServiceTest."""

from datetime import UTC, datetime

import pytest
from freezegun import freeze_time

from apps.common.exceptions import BusinessRuleException
from apps.lineups import services as lineups
from apps.lineups.models import EffectiveLineupPeriod, LineupPeriodOrigin
from apps.matchdays import formations
from apps.matchdays.models import Formation, FormationSource, Matchday

from .conftest import auth_client
from .factories import (
    AdminFactory,
    EditionFactory,
    FantaTeamFactory,
    LeagueFactory,
    UserFactory,
    build_edition_rosters,
    give_roster,
)

pytestmark = pytest.mark.django_db
BACKFILL = datetime(2026, 7, 23, 22, tzinfo=UTC)  # 2026-07-24T00:00+02:00
FRIDAY = datetime(2026, 7, 30, 22, tzinfo=UTC)
WEDNESDAY = "2026-07-29T10:00:00Z"
ROLES = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]


@pytest.fixture
def ctx():
    edition = EditionFactory(starts_at=BACKFILL)
    teams = list(build_edition_rosters(edition, 10).values())
    owner = UserFactory(username="mago")
    league = LeagueFactory(edition=edition, participant_count=5)
    team = FantaTeamFactory(league=league, owner=owner)
    starters, reserves = teams[0], teams[1]
    give_roster(team, starters + reserves)
    return {"league": league, "team": team, "owner": owner, "starters": starters, "reserves": reserves,
            "others": teams[2]}


def players(entries):
    return [e.player for e in entries]


def periods(team, origin=None):
    qs = EffectiveLineupPeriod.objects.filter(fanta_team=team)
    return list(qs.filter(origin=origin) if origin else qs)


@freeze_time(WEDNESDAY)
def test_programma_cinque_periodi_dal_venerdi_e_chiude_quelli_correnti(ctx):
    team = ctx["team"]
    lineups.create_backfill_periods(team, players(ctx["starters"]), datetime(2026, 7, 24, tzinfo=UTC))
    lineups.schedule(ctx["owner"], team.id, players(ctx["reserves"]))
    old = EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_from=datetime(2026, 7, 24, tzinfo=UTC))
    assert all(p.effective_until == FRIDAY for p in old)
    new = EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_from=FRIDAY)
    assert new.count() == 5 and {p.origin for p in new} == {LineupPeriodOrigin.USER}


@freeze_time(WEDNESDAY)
def test_sostituisce_i_periodi_pendenti_se_si_salva_di_nuovo(ctx):
    team = ctx["team"]
    lineups.schedule(ctx["owner"], team.id, players(ctx["starters"]))
    lineups.schedule(ctx["owner"], team.id, players(ctx["reserves"]))
    assert len(periods(team)) == 5
    assert {p.player_id for p in periods(team)} == {e.player_id for e in ctx["reserves"]}
    assert all(p.effective_from == FRIDAY and p.effective_until is None for p in periods(team))


@freeze_time("2026-07-31T10:00:00Z")
def test_rifiuta_fuori_dalla_finestra_di_roma(ctx):
    with pytest.raises(BusinessRuleException, match="martedì"):
        lineups.schedule(ctx["owner"], ctx["team"].id, players(ctx["starters"]))


@freeze_time(WEDNESDAY)
def test_rifiuta_nelle_leghe_a_rosa_fissa(ctx):
    league = ctx["league"]
    league.participant_count = 6
    league.save()
    with pytest.raises(BusinessRuleException, match="almeno 6"):
        lineups.schedule(ctx["owner"], ctx["team"].id, players(ctx["starters"]))


@freeze_time(WEDNESDAY)
def test_conferma_crea_lo_storico_quando_non_esistono_periodi(ctx):
    lineups.schedule_confirmed(ctx["owner"], ctx["team"].id, players(ctx["starters"]))
    created = periods(ctx["team"])
    assert len(created) == 5
    assert all(p.effective_from == BACKFILL and p.origin == LineupPeriodOrigin.BACKFILL for p in created)


@freeze_time(WEDNESDAY)
def test_conferma_ripara_periodi_solo_futuri_senza_sovrascriverli(ctx):
    team = ctx["team"]
    lineups.schedule(ctx["owner"], team.id, players(ctx["starters"]))
    lineups.schedule_confirmed(ctx["owner"], team.id, players(ctx["starters"]))
    historical = periods(team, LineupPeriodOrigin.BACKFILL)
    assert len(historical) == 5 and all(p.effective_until == FRIDAY for p in historical)
    future = periods(team, LineupPeriodOrigin.USER)
    assert len(future) == 5 and all(p.effective_until is None for p in future)
    lineups.schedule_confirmed(ctx["owner"], team.id, players(ctx["reserves"]))
    assert {p.player_id for p in EffectiveLineupPeriod.objects.filter(fanta_team=team, effective_until=None)} == \
        {e.player_id for e in ctx["reserves"]}


@freeze_time(WEDNESDAY)
def test_player_attivo_all_istante_e_selezione_programmata(ctx):
    team = ctx["team"]
    lineups.create_backfill_periods(team, players(ctx["starters"]), BACKFILL)
    lineups.schedule(ctx["owner"], team.id, players(ctx["reserves"]))
    mid_now = lineups.active_period_at(team.id, "MID", datetime(2026, 7, 29, 12, tzinfo=UTC))
    mid_later = lineups.active_period_at(team.id, "MID", datetime(2026, 8, 1, 10, tzinfo=UTC))
    assert mid_now.player_id == ctx["starters"][2].player_id
    assert mid_later.player_id == ctx["reserves"][2].player_id
    assert {p.id for p in lineups.scheduled_players(team.id)} == {e.player_id for e in ctx["reserves"]}
    assert {p.id for p in lineups.active_players_at(team.id, datetime(2026, 7, 29, tzinfo=UTC))} == \
        {e.player_id for e in ctx["starters"]}


def test_formazione_non_valida(ctx):
    with pytest.raises(BusinessRuleException, match="un player per ruolo"):
        lineups.validate_five_roles(ctx["team"], players(ctx["starters"][:4] + ctx["reserves"][3:4]))


# --------------------------------------------------------------------------- backfill
def test_backfill_salta_formazioni_non_valide_e_rose_fisse_incomplete(ctx):
    team = ctx["team"]
    day1 = Matchday.objects.create(league=ctx["league"], numero=1)
    day2 = Matchday.objects.create(league=ctx["league"], numero=2)
    valid = Formation.objects.create(fanta_team=team, matchday=day1, source=FormationSource.SUBMITTED)
    valid.titolari.set(players(ctx["starters"]))
    invalid = Formation.objects.create(fanta_team=team, matchday=day2, source=FormationSource.SUBMITTED)
    invalid.titolari.set(players(ctx["starters"][:4]))
    big = LeagueFactory(edition=ctx["league"].edition, participant_count=6)
    incomplete = FantaTeamFactory(league=big)
    give_roster(incomplete, ctx["others"][:4])
    complete = FantaTeamFactory(league=big)
    give_roster(complete, ctx["starters"])
    assert lineups.backfill_all() == 2
    assert {p.player_id for p in periods(team)} == {e.player_id for e in ctx["starters"]}
    assert not periods(incomplete) and len(periods(complete)) == 5
    assert lineups.backfill_all() == 0


# --------------------------------------------------------------------------- FormationService
@freeze_time(WEDNESDAY)
def test_imposta_una_formazione_valida_e_casi_di_errore(ctx):
    day = Matchday.objects.create(league=ctx["league"], numero=1)
    ids = [e.player_id for e in ctx["starters"]]
    response = formations.imposta(ctx["owner"], ctx["team"].id, day.id, ids)
    assert sorted(response["titolari"]) == sorted(e.player.nickname for e in ctx["starters"])
    assert response["source"] == FormationSource.SUBMITTED and response["editable"]
    with pytest.raises(BusinessRuleException, match="non appartiene alla rosa"):
        formations.imposta(ctx["owner"], ctx["team"].id, day.id, ids[:4] + [ctx["others"][4].player_id])
    with pytest.raises(BusinessRuleException, match="proprietario"):
        formations.imposta(UserFactory(), ctx["team"].id, day.id, ids)
    with pytest.raises(BusinessRuleException, match="titolari diversi"):
        formations.imposta(ctx["owner"], ctx["team"].id, day.id, ids[:4])
    ctx["league"].auction_open = True
    ctx["league"].save()
    with pytest.raises(BusinessRuleException, match="asta"):
        formations.imposta(ctx["owner"], ctx["team"].id, day.id, ids)
    ctx["league"].auction_open = False
    ctx["league"].save()
    day.chiusa = True
    day.save()
    with pytest.raises(BusinessRuleException, match="chiusa"):
        formations.imposta(ctx["owner"], ctx["team"].id, day.id, ids)


@freeze_time(WEDNESDAY)
def test_finestra_esposta_e_bloccata_per_le_rose_fisse(ctx):
    window = formations.lineup_window(ctx["owner"], ctx["team"].id)
    assert window["editable"] and window["next_effective_at"] == FRIDAY
    with pytest.raises(BusinessRuleException, match="Non sei il proprietario"):
        formations.lineup_window(UserFactory(), ctx["team"].id)
    ctx["league"].participant_count = 6
    ctx["league"].save()
    assert not formations.lineup_window(ctx["owner"], ctx["team"].id)["editable"]


@freeze_time(WEDNESDAY)
def test_lineup_settimanale_selezione_ed_effettivi_separati(ctx):
    team = ctx["team"]
    lineups.create_backfill_periods(team, players(ctx["starters"]), BACKFILL)
    response = formations.schedule_lineup(ctx["owner"], team.id,
                                          {"titolari_ids": [e.player_id for e in ctx["reserves"]]})
    assert {p["id"] for p in response["players"]} == {e.player_id for e in ctx["reserves"]}
    assert {p["id"] for p in response["effective_players"]} == {e.player_id for e in ctx["starters"]}
    assert response["next_effective_at"] == FRIDAY
    assert not Formation.objects.exists()
    found = formations.find_lineup(ctx["owner"], team.id)
    assert {p["nickname"] for p in found["players"]} == {e.player.nickname for e in ctx["reserves"]}
    with pytest.raises(BusinessRuleException, match="un player per ruolo"):
        formations.schedule_lineup(ctx["owner"], team.id, {"titolari_ids": [
            e.player_id for e in ctx["starters"][:4] + ctx["reserves"][:1]]})
    formations.schedule_lineup(AdminFactory(), team.id, {"titolari_ids": [e.player_id for e in ctx["starters"]]})


@freeze_time(WEDNESDAY)
def test_conferma_rosa_automatica_nelle_leghe_grandi_e_fuori_finestra(ctx):
    league = LeagueFactory(edition=ctx["league"].edition, participant_count=6)
    owner = UserFactory()
    team = FantaTeamFactory(league=league, owner=owner)
    give_roster(team, ctx["others"])
    day = Matchday.objects.create(league=league, numero=1)
    response = formations.confirm(owner, team.id, day.id)
    assert response["confirmed"] and len(response["titolari"]) == 5
    assert len(periods(team)) == 5
    assert formations.confirm_all(AdminFactory(), league.id, day.id) == 1
    with pytest.raises(BusinessRuleException, match="ADMIN globale"):
        formations.confirm_all(owner, league.id, day.id)
    with freeze_time("2026-07-31T10:00:00Z"), pytest.raises(BusinessRuleException, match="martedì"):
        formations.confirm(owner, team.id, day.id)


@freeze_time(WEDNESDAY)
def test_sicurezza_dei_controller_formazioni(ctx, api):
    url = f"/api/fanta-teams/{ctx['team'].id}/formazioni/lineup"
    assert api.put(url, {"titolariIds": [1]}, format="json").status_code == 401
    owner = auth_client(ctx["owner"])
    ok = owner.put(url, {"titolariIds": [e.player_id for e in ctx["starters"]]}, format="json")
    assert ok.status_code == 200 and set(ok.json()) >= {"players", "effectivePlayers", "editable",
                                                       "nextEffectiveAt"}
    day = Matchday.objects.create(league=ctx["league"], numero=1)
    confirm_all = f"/api/admin/leagues/{ctx['league'].id}/matchdays/{day.id}/formations/confirm-all"
    assert owner.post(confirm_all).status_code == 403
    assert auth_client(AdminFactory()).post(confirm_all).json() == {"confirmedTeams": 1}
    assert owner.get(f"/api/fanta-teams/{ctx['team'].id}/formazioni/window").json()["editable"] is True
    history = owner.get(f"/api/fanta-teams/{ctx['team'].id}/formazioni").json()
    assert history[0]["confirmed"] is True
    single = owner.get(f"/api/fanta-teams/{ctx['team'].id}/formazioni/{day.id}")
    assert single.status_code == 200
    put = owner.put(f"/api/fanta-teams/{ctx['team'].id}/formazioni",
                    {"matchdayId": day.id, "titolariIds": [e.player_id for e in ctx["reserves"]]}, format="json")
    assert put.status_code == 200 and put.json()["source"] == "SUBMITTED"
    assert owner.post(f"/api/fanta-teams/{ctx['team'].id}/formazioni/{day.id}/confirm").status_code == 200
    assert owner.get(f"/api/fanta-teams/{ctx['team'].id}/formazioni/9999").status_code == 404
