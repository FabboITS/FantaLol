"""Porting di MatchdayLifecycleServiceTest e MatchdayScoringServiceTest + giornate regionali generalizzate."""

from datetime import UTC, date, datetime, timedelta

import pytest
from freezegun import freeze_time

from apps.common.exceptions import BusinessRuleException
from apps.lineups import services as lineups
from apps.matchdays import scoring, services
from apps.matchdays.models import Formation, FormationSource, Matchday, MatchdayStatus, PlayerStat
from apps.scoring.formulas import game_score

from .conftest import auth_client
from .factories import (
    EditionFactory,
    FantaTeamFactory,
    LeagueFactory,
    UserFactory,
    add_game,
    add_match,
    add_stat,
    build_edition_rosters,
    give_roster,
)

pytestmark = pytest.mark.django_db
WEEK_START = datetime(2026, 7, 26, 22, tzinfo=UTC)  # lunedì 27/07 00:00 Europe/Rome


@pytest.fixture
def ctx():
    edition = EditionFactory(starts_at=datetime(2026, 7, 20, tzinfo=UTC))
    rosters = build_edition_rosters(edition, 10)
    teams = list(rosters)
    creator = UserFactory(username="creator")
    league = LeagueFactory(admin=creator, edition=edition)
    return {"edition": edition, "rosters": rosters, "teams": teams, "creator": creator, "league": league}


# --------------------------------------------------------------------------- ciclo di vita
def test_creare_la_prima_giornata_avvia_la_competizione_e_apre_l_asta(ctx):
    FantaTeamFactory(league=ctx["league"])
    day = services.create(ctx["creator"], league_id=ctx["league"].id, numero=1, descrizione="Week 1",
                          data=date(2026, 7, 29))
    ctx["league"].refresh_from_db()
    assert ctx["league"].participant_count == 1 and ctx["league"].auction_open
    response = services.matchday_response(day)
    assert response["auction_locked"] is True
    assert (day.starts_at, day.ends_at) == (WEEK_START, WEEK_START + timedelta(days=7))


def test_rifiuta_una_seconda_giornata_aperta_e_numeri_duplicati(ctx):
    services.create(ctx["creator"], league_id=ctx["league"].id, numero=1, descrizione=None, data=None)
    with pytest.raises(BusinessRuleException, match="giornata aperta"):
        services.create(ctx["creator"], league_id=ctx["league"].id, numero=2, descrizione=None, data=None)
    with pytest.raises(BusinessRuleException, match="Solo l'admin della lega"):
        services.create(UserFactory(), league_id=ctx["league"].id, numero=3, descrizione=None, data=None)


def test_statistiche_e_chiusura_rifiutate_ad_asta_aperta(ctx, admin):
    day = services.create(ctx["creator"], league_id=ctx["league"].id, numero=1, descrizione=None, data=None)
    player = ctx["rosters"][ctx["teams"][0]][0].player
    with pytest.raises(BusinessRuleException, match="asta"):
        services.insert_stats(admin, day.id, {"lec_player_id": player.id})
    with pytest.raises(BusinessRuleException, match="asta"):
        services.close(ctx["creator"], day.id)


def test_inserimento_manuale_statistiche_solo_admin_globale(ctx, admin):
    day = Matchday.objects.create(league=ctx["league"], numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    support = ctx["rosters"][ctx["teams"][0]][4].player
    with pytest.raises(BusinessRuleException, match="amministratore globale"):
        services.insert_stats(ctx["creator"], day.id, {"lec_player_id": support.id})
    stat = services.insert_stats(admin, day.id, {"lec_player_id": support.id, "kills": 1, "morti": 1,
                                                 "assist": 1, "cs": 100, "vision_score": 50, "vittoria": True})
    assert stat.fantavoto == pytest.approx(6.95, abs=1e-4) and stat.source == "MANUAL"


def test_media_dei_cinque_player_con_zero_per_statistiche_mancanti(ctx, admin):
    league = ctx["league"]
    league.participant_count = 5
    league.save()
    team = FantaTeamFactory(league=league, owner=ctx["creator"])
    starters = ctx["rosters"][ctx["teams"][0]]
    give_roster(team, starters)
    lineups.create_backfill_periods(team, [e.player for e in starters], ctx["edition"].starts_at)
    day = Matchday.objects.create(league=league, numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    for entry, score in zip(starters[:4], (10, 8, 6, 4), strict=True):
        PlayerStat.objects.create(matchday=day, player=entry.player, fantavoto=score, source="MANUAL")
    services.close(ctx["creator"], day.id)
    formation = Formation.objects.get(fanta_team=team, matchday=day)
    assert formation.punteggio_totale == pytest.approx(5.6)
    day.refresh_from_db()
    assert day.chiusa and day.status == MatchdayStatus.CLOSED
    team.refresh_from_db()
    assert team.punti == pytest.approx(5.6)
    with pytest.raises(BusinessRuleException, match="già chiusa"):
        services.close(ctx["creator"], day.id)


def test_prima_formazione_mancante_vale_zero(ctx):
    team = FantaTeamFactory(league=ctx["league"])
    day = Matchday.objects.create(league=ctx["league"], numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    services.close(ctx["creator"], day.id)
    formation = Formation.objects.get(fanta_team=team, matchday=day)
    assert formation.source == FormationSource.MISSING and formation.punteggio_totale == 0


def test_rinvio_e_giornata_in_attesa(ctx):
    day = Matchday.objects.create(league=ctx["league"], numero=1)
    assert services.mark_waiting(ctx["creator"], day.id).status == MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES
    day.chiusa = True
    day.save()
    with pytest.raises(BusinessRuleException):
        services.mark_waiting(ctx["creator"], day.id)


# --------------------------------------------------------------------------- punteggi dalle statistiche reali
def _series(ctx, team_a, team_b, begin, games):
    """games: lista di (vincitore, {player: (k, d, a, cs, vs)})."""
    match = add_match(ctx["edition"], team_a, team_b, begin=begin, winner=team_a,
                      score=(len(games), 0), stats_complete=True)
    for number, (winner, lines) in enumerate(games, start=1):
        game = add_game(match, number, played_at=begin + timedelta(hours=number))
        for player, (k, d, a, cs, vs) in lines.items():
            entry = next(e for es in ctx["rosters"].values() for e in es if e.player == player)
            add_stat(game, player, kills=k, deaths=d, assists=a, cs=cs, vision=vs, win=entry.team == winner,
                     team=entry.team)
    return match


def test_media_per_serie_somma_tra_serie_e_cambio_di_titolare(ctx):
    a, b, c = ctx["teams"][:3]
    mid_a = ctx["rosters"][a][2].player
    mid_b = ctx["rosters"][b][2].player
    _series(ctx, a, b, WEEK_START + timedelta(days=4), [(a, {mid_a: (2, 1, 3, 200, 0), mid_b: (1, 2, 1, 100, 0)}),
                                                       (a, {mid_a: (4, 0, 2, 300, 0)})])
    _series(ctx, a, c, WEEK_START + timedelta(days=5), [(c, {mid_a: (0, 3, 1, 150, 0)})])
    day = Matchday.objects.create(league=ctx["league"], numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    assert scoring.recompute_player_stats(day) == 2
    stat = PlayerStat.objects.get(matchday=day, player=mid_a)
    first_series = (game_score("MID", 2, 1, 3, 200, 0, True) + game_score("MID", 4, 0, 2, 300, 0, True)) / 2
    second_series = game_score("MID", 0, 3, 1, 150, 0, False)
    assert stat.fantavoto == pytest.approx(first_series + second_series, abs=1e-9)
    assert (stat.games_played, stat.series_played, stat.wins, stat.kills) == (3, 2, 2, 6)
    assert not day.provisional

    # FantaTeam: il MID cambia tra le due serie → ogni serie è attribuita al titolare del momento.
    team = FantaTeamFactory(league=ctx["league"])
    give_roster(team, [ctx["rosters"][a][2], ctx["rosters"][b][2]])
    from apps.lineups.models import EffectiveLineupPeriod

    switch = WEEK_START + timedelta(days=5)
    EffectiveLineupPeriod.objects.create(fanta_team=team, role="MID", player=mid_b,
                                         effective_from=ctx["edition"].starts_at, effective_until=switch,
                                         origin="USER")
    EffectiveLineupPeriod.objects.create(fanta_team=team, role="MID", player=mid_a, effective_from=switch,
                                         origin="USER")
    total, slots = scoring.regional_team_matchday_score(team.id, day)
    expected_mid = game_score("MID", 1, 2, 1, 100, 0, False) + second_series
    assert slots["MID"]["score"] == pytest.approx(expected_mid, abs=1e-9)
    assert total == pytest.approx(expected_mid / 5, abs=1e-9)


def test_giornata_provvisoria_finche_mancano_statistiche_e_chiusura_automatica(ctx):
    a, b = ctx["teams"][:2]
    ctx["league"].participant_count = 2
    ctx["league"].save()
    match = _series(ctx, a, b, WEEK_START + timedelta(days=4), [(a, {ctx["rosters"][a][0].player: (1, 1, 1, 100,
                                                                                                    0)})])
    match.stats_complete = False
    match.save()
    day = Matchday.objects.create(league=ctx["league"], numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    scoring.recompute_player_stats(day)
    day.refresh_from_db()
    assert day.provisional
    with freeze_time(WEEK_START + timedelta(days=8)):
        assert services.auto_close_matchdays() == {"closed": 0, "waiting": 0}
        match.stats_complete = True
        match.save()
        assert services.auto_close_matchdays() == {"closed": 1, "waiting": 0}
    day.refresh_from_db()
    assert day.chiusa and not day.provisional


def test_serie_rinviata_mette_la_giornata_in_attesa(ctx):
    a, b = ctx["teams"][:2]
    add_match(ctx["edition"], a, b, begin=WEEK_START + timedelta(days=4), status="postponed")
    day = Matchday.objects.create(league=ctx["league"], numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    with freeze_time(WEEK_START + timedelta(days=8)):
        assert services.auto_close_matchdays() == {"closed": 0, "waiting": 1}
    day.refresh_from_db()
    assert day.status == MatchdayStatus.WAITING_FOR_POSTPONED_MATCHES and not day.chiusa
    ctx["league"].settings = {"auto_close_matchdays": False}
    ctx["league"].save()
    with freeze_time(WEEK_START + timedelta(days=8)):
        assert services.auto_close_matchdays() == {"closed": 0, "waiting": 0}


def test_correzione_manuale_ricalcola_la_giornata(ctx, admin_client):
    a, b = ctx["teams"][:2]
    top = ctx["rosters"][a][0].player
    match = _series(ctx, a, b, WEEK_START + timedelta(days=4), [(a, {top: (1, 1, 1, 100, 0)})])
    day = Matchday.objects.create(league=ctx["league"], numero=1, starts_at=WEEK_START,
                                  ends_at=WEEK_START + timedelta(days=7))
    game = match.games.get()
    response = admin_client.put(f"/api/admin/games/{game.leaguepedia_game_id}/players/{top.id}",
                                {"kills": 5}, format="json")
    assert response.status_code == 200 and response.json()["overridden"] is True
    assert PlayerStat.objects.get(matchday=day, player=top).kills == 5
    assert admin_client.delete(f"/api/admin/games/{game.id}/players/{top.id}/override").json()["kills"] == 1
    assert PlayerStat.objects.get(matchday=day, player=top).kills == 1
    not_played = admin_client.put(f"/api/admin/lec/games/{game.id}/players/{top.id}", {"participated": False},
                                  format="json")
    assert not_played.json()["participated"] is False
    assert not PlayerStat.objects.filter(matchday=day, player=top).exists()


def test_api_giornate(ctx):
    client = auth_client(ctx["creator"])
    created = client.post("/api/matchdays", {"leagueId": ctx["league"].id, "numero": 1, "descrizione": "Week 1",
                                             "data": "2026-07-29"}, format="json")
    assert created.status_code == 201
    body = created.json()
    assert set(body) >= {"id", "leagueId", "leagueNome", "numero", "descrizione", "data", "chiusa", "status",
                         "auctionLocked"}
    assert body["data"] == "2026-07-29" and body["status"] == "OPEN"
    assert client.get(f"/api/matchdays?leagueId={ctx['league'].id}").json()[0]["id"] == body["id"]
    assert client.get(f"/api/matchdays/{body['id']}").json()["numero"] == 1
    assert client.get(f"/api/matchdays/{body['id']}/stats").json() == []
    assert client.post(f"/api/matchdays/{body['id']}/chiudi").status_code == 422
    assert client.post(f"/api/matchdays/{body['id']}/waiting-for-postponed").status_code == 422
    assert client.get("/api/matchdays/9999").status_code == 404
