"""Porting di CumulativeScoringServiceTest, CumulativeDataFreshnessServiceTest e dei test di sicurezza
di CumulativeScoringController; dati per competizione (alias /api/lec/*)."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.common.exceptions import ResourceNotFoundException
from apps.esports.models import GamePlayerStatOverride
from apps.esports.observations import Observation, observations
from apps.lineups.models import EffectiveLineupPeriod
from apps.providers.sync_state import record_failure, record_success
from apps.scoring import cumulative

from .conftest import auth_client
from .factories import (
    EditionFactory,
    FantaTeamFactory,
    LeagueFactory,
    PlayerFactory,
    UserFactory,
    add_game,
    add_match,
    add_stat,
    build_edition_rosters,
)

pytestmark = pytest.mark.django_db
FRIDAY = datetime(2026, 7, 31, tzinfo=UTC)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def obs(player, played_at: str, score: float) -> Observation:
    return Observation(game_id=hash((player.id, played_at)), match_id=1, game_number=1, leaguepedia_game_id=None,
                       player_id=player.id, nickname=player.nickname, team_name="", role="MID", champion="",
                       kills=0, deaths=0, assists=0, cs=0, vision_score=0, win=False,
                       played_at=datetime.fromisoformat(played_at.replace("Z", "+00:00")), participated=True,
                       overridden=False, complete=True, score=score)


@pytest.fixture
def ctx(monkeypatch):
    league = LeagueFactory()
    team = FantaTeamFactory(league=league, nome="Blue Phoenix")
    p = {name: PlayerFactory(nickname=name) for name in
         ("Old Mid", "New Mid", "Bench Mid", "Top", "Jungle", "Adc", "Support")}

    def period(t, role, player, start, end=None):
        EffectiveLineupPeriod.objects.create(fanta_team=t, role=role, player=player, effective_from=start,
                                             effective_until=end, origin="USER")

    period(team, "TOP", p["Top"], EPOCH)
    period(team, "JUNGLE", p["Jungle"], EPOCH)
    period(team, "MID", p["Old Mid"], EPOCH, FRIDAY)
    period(team, "MID", p["New Mid"], FRIDAY)
    period(team, "ADC", p["Adc"], EPOCH)
    period(team, "SUPPORT", p["Support"], EPOCH)
    stats = [obs(p["Old Mid"], "2026-07-28T12:00:00Z", 10), obs(p["Old Mid"], "2026-07-29T12:00:00Z", 20),
             obs(p["Old Mid"], "2026-07-30T12:00:00Z", 30), obs(p["New Mid"], "2026-08-01T12:00:00Z", 40),
             obs(p["Bench Mid"], "2026-07-29T12:00:00Z", 100), obs(p["Top"], "2026-07-29T12:00:00Z", 11),
             obs(p["Jungle"], "2026-07-29T12:00:00Z", 12), obs(p["Adc"], "2026-07-29T12:00:00Z", 13)]
    state = {"stats": stats}

    def fake_observations(edition_id=None, player_ids=None, **kwargs):
        rows = state["stats"]
        return [o for o in rows if player_ids is None or o.player_id in player_ids]

    monkeypatch.setattr(cumulative, "observations", fake_observations)
    return {"league": league, "team": team, "p": p, "state": state, "period": period}


def test_media_del_player_usa_solo_i_game_giocati(ctx):
    score = cumulative.player_score(ctx["league"].edition_id, ctx["p"]["Old Mid"].id)
    assert score["games_played"] == 3 and score["average"] == 20.0
    assert cumulative.player_score(ctx["league"].edition_id, ctx["p"]["Bench Mid"].id)["average"] == 100.0
    with pytest.raises(ResourceNotFoundException):
        cumulative.player_score(ctx["league"].edition_id, ctx["p"]["Support"].id)


def test_il_team_attribuisce_solo_il_player_attivo_al_momento_del_game(ctx):
    mid = next(s for s in cumulative.team_score(ctx["team"])["slots"] if s["role"] == "MID")
    assert mid["games_played"] == 4 and mid["average"] == 25.0
    assert mid["contributing_players"] == ["Old Mid", "New Mid"]


def test_titolare_senza_osservazioni_rende_il_team_provvisorio(ctx):
    score = cumulative.team_score(ctx["team"])
    support = next(s for s in score["slots"] if s["role"] == "SUPPORT")
    assert {s["role"] for s in score["slots"]} == {"TOP", "JUNGLE", "MID", "ADC", "SUPPORT"}
    assert support["games_played"] == 0 and support["average"] is None and support["status"] == "awaiting-data"
    assert score["overall_total"] is None and score["provisional"] is True


def test_totale_somma_ogni_game_giocato_dalla_rosa_storicamente_attiva(ctx):
    p = ctx["p"]
    ctx["state"]["stats"] = [obs(p["Top"], "2026-07-29T12:00:00Z", 11), obs(p["Jungle"], "2026-07-29T12:00:00Z", 12),
                             obs(p["Old Mid"], "2026-07-29T12:00:00Z", 10),
                             obs(p["New Mid"], "2026-08-01T12:00:00Z", 40),
                             obs(p["Adc"], "2026-07-29T12:00:00Z", 13),
                             obs(p["Support"], "2026-07-29T12:00:00Z", 14)]
    assert cumulative.team_score(ctx["team"])["overall_total"] == 100.0


def test_classifica_di_lega_attribuzione_e_ordine(ctx):
    p = ctx["p"]
    zeta = FantaTeamFactory(league=ctx["league"], nome="Zeta")
    ghost = FantaTeamFactory(league=ctx["league"], nome="Ghost")
    zeta_players = [PlayerFactory(nickname=f"Zeta {r}") for r in ("Top", "Jungle", "Mid", "Adc", "Support")]
    for role, player in zip(("TOP", "JUNGLE", "MID", "ADC", "SUPPORT"), zeta_players, strict=True):
        ctx["period"](zeta, role, player, EPOCH)
    for role, name in (("TOP", "Top"), ("JUNGLE", "Jungle"), ("MID", "Old Mid"), ("ADC", "Adc")):
        ctx["period"](ghost, role, p[name], EPOCH)
    ctx["state"]["stats"] = [obs(p[n], "2026-07-29T12:00:00Z", 10) for n in ("Top", "Jungle", "Old Mid", "Adc",
                                                                             "Support")]
    ctx["state"]["stats"] += [obs(p["New Mid"], "2026-08-01T12:00:00Z", 30)]
    ctx["state"]["stats"] += [obs(z, "2026-07-29T12:00:00Z", 50) for z in zeta_players]
    ranking = cumulative.league_ranking(ctx["league"])
    assert [r["team_name"] for r in ranking] == ["Zeta", "Blue Phoenix", "Ghost"]
    mid = next(s for s in ranking[1]["slots"] if s["role"] == "MID")
    assert mid["contributing_players"] == ["Old Mid", "New Mid"]
    assert ranking[2]["provisional"] is True


# --------------------------------------------------------------------------- override e partecipazione
def test_override_admin_attiva_un_non_partecipante_e_puo_escludere_un_game():
    edition = EditionFactory()
    rosters = build_edition_rosters(edition, 2)
    a, b = list(rosters)
    mid = rosters[a][2].player
    match = add_match(edition, a, b, begin=datetime(2026, 7, 28, 12, tzinfo=UTC), winner=a)
    game = add_game(match)
    override = GamePlayerStatOverride.objects.create(game=game, player=mid, participated=True, kills=5)
    rows = observations(edition_id=edition.id)
    assert len(rows) == 1 and rows[0].overridden and rows[0].kills == 5
    override.participated = False
    override.save()
    assert observations(edition_id=edition.id) == []
    add_stat(game, rosters[b][2].player, kills=1)
    assert [o.nickname for o in observations(edition_id=edition.id)] == [rosters[b][2].player.nickname]


# --------------------------------------------------------------------------- freschezza e sicurezza
def test_freschezza_dei_dati_cumulativi(api):
    edition = EditionFactory()
    competition = edition.competition
    body = api.get("/api/lec/cumulative-performances").json()
    assert body == {"status": "awaiting-data", "lastUpdatedAt": None, "provisional": True, "items": []}
    record_success("LEAGUEPEDIA", competition)
    fresh = api.get("/api/competitions/lec/cumulative-performances").json()
    assert fresh["status"] == "fresh" and fresh["lastUpdatedAt"] and fresh["provisional"] is False
    record_failure("LEAGUEPEDIA", competition, "boom")
    stale = api.get("/api/lec/cumulative-performances").json()
    assert stale["status"] == "stale" and stale["lastUpdatedAt"] == fresh["lastUpdatedAt"]
    assert list(stale) == ["status", "lastUpdatedAt", "provisional", "items"]


def test_classifica_privata_e_punteggio_team_richiedono_membership(api):
    league = LeagueFactory()
    member = UserFactory()
    team = FantaTeamFactory(league=league, owner=member)
    url = f"/api/leagues/{league.id}/cumulative-ranking"
    assert api.get(url).status_code == 401
    assert auth_client(UserFactory()).get(url).status_code == 403
    response = auth_client(member).get(url)
    assert response.status_code == 200 and response.json()["status"] == "awaiting-data"
    assert response.json()["items"][0]["teamName"] == team.nome
    assert auth_client(member).get(f"/api/fanta-teams/{team.id}/cumulative-score").json()["provisional"] is True
    assert auth_client(UserFactory()).get(f"/api/fanta-teams/{team.id}/cumulative-score").status_code == 403


def test_dati_per_competizione_e_alias_lec(api):
    edition = EditionFactory()
    rosters = build_edition_rosters(edition, 2)
    a, b = list(rosters)
    match = add_match(edition, a, b, begin=datetime(2026, 7, 28, 12, tzinfo=UTC), winner=a, score=(2, 0))
    for number in (1, 2):
        game = add_game(match, number, played_at=match.begin_at + timedelta(hours=number), winner=a)
        for entry in rosters[a] + rosters[b]:
            add_stat(game, entry.player, kills=2, deaths=0 if entry.team == a else 2, assists=3, cs=200,
                     vision=40, win=entry.team == a, team=entry.team)
    standings = api.get("/api/lec/standings").json()
    assert standings["items"][0] == {"position": 1, "teamName": a.name, "seriesWins": 1, "seriesLosses": 0}
    assert api.get("/api/competitions/LEC/standings").json()["items"] == standings["items"]
    performances = api.get("/api/competitions/lec/performances").json()["items"]
    assert performances[0]["gamesPlayed"] == 2 and performances[0]["teamName"] == a.name
    matches = api.get("/api/lec/matches").json()["items"]
    assert matches[0]["name"] == match.name and len(matches[0]["games"]) == 2
    game_id = matches[0]["games"][0]["id"]
    detail = api.get(f"/api/lec/matches/{matches[0]['id']}/games/{game_id}").json()
    player = detail["players"][0]
    assert player["perfectKda"] is True and player["kda"] is None and player["fantasyScore"] is not None
    assert player["championImagePath"] == "/Player_immage/Champions/unknown.svg"
    assert api.get(f"/api/lec/matches/{matches[0]['id']}/games/nope").status_code == 404
    assert api.get("/api/competitions/xyz/standings").status_code == 404
    cumulative_items = api.get("/api/lec/cumulative-performances").json()["items"]
    assert cumulative_items[0]["gamesPlayed"] == 2


def test_competizioni_ed_edizioni(api):
    EditionFactory(name="LEC 2026 Summer")
    competitions = api.get("/api/competitions").json()
    assert [c["code"] for c in competitions] == ["LEC", "LCK", "LPL", "WORLDS"]
    assert competitions[0]["currentEdition"]["name"] == "LEC 2026 Summer"
    assert competitions[0]["currentEdition"]["lineupStrategy"] == "FIXED_WEEKLY_WINDOW"
    editions = api.get("/api/competitions/lec/editions").json()
    assert editions[0]["ruleset"] == "REGIONAL"
    assert api.get("/api/competitions/nope/editions").status_code == 404
