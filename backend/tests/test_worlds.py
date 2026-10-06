"""Regolamento WORLDS: limiti per team, budget 100→105, cambi, sostituzioni, capitano, somma e spareggi,
più una simulazione end-to-end di un torneo con fixture."""

from datetime import UTC, datetime, timedelta

import pytest
from django.core.management import call_command
from freezegun import freeze_time

from apps.common.exceptions import BusinessRuleException
from apps.competitions.models import Competition, CompetitionEdition, Stage, ensure_worlds_stages
from apps.esports.models import EditionRoster
from apps.leagues.models import RosterEntry
from apps.matchdays import services as matchdays
from apps.matchdays.models import Formation, Matchday
from apps.scoring.formulas import game_score
from apps.worlds import pricing, services
from apps.worlds.models import Transfer

from .conftest import auth_client
from .factories import (
    FantaTeamFactory,
    LeagueFactory,
    PlayerFactory,
    TeamFactory,
    UserFactory,
    add_game,
    add_match,
    add_stat,
)

pytestmark = pytest.mark.django_db
ROLES = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]


def day(d: int, hour: int = 8) -> datetime:
    month = 10 if d >= 15 else 11
    return datetime(2026, month, d, hour, tzinfo=UTC)


# --------------------------------------------------------------------------- sostituzioni e capitano (puro)
def test_sostituzioni_automatiche_solo_pari_ruolo_in_ordine_di_panchina():
    roles = {1: "TOP", 2: "JUNGLE", 3: "MID", 4: "ADC", 5: "SUPPORT", 6: "MID", 7: "MID", 8: "TOP"}
    scores = {1: 10.0, 2: 8.0, 4: 6.0, 5: 4.0, 7: 9.0, 8: 20.0}
    result = services.score_formation(
        [1, 2, 3, 4, 5], [6, 7, 8], captain=1, vice=2, roles=roles, scores=scores
    )
    by_role = {e["role"]: e for e in result["effective"]}
    assert by_role["MID"]["id"] == 7 and by_role["MID"]["substituted_for"] == 3  # il 6 non ha giocato
    assert result["base"] == 10 + 8 + 9 + 6 + 4
    assert result["bonus"] == 10 and result["captain_points"] == 20 and result["doubled"] == 1


def test_nessun_cambio_di_ruolo_e_raddoppio_al_vice():
    roles = {1: "TOP", 2: "JUNGLE", 3: "MID", 4: "ADC", 5: "SUPPORT", 6: "ADC"}
    scores = {2: 8.0, 3: 5.0, 4: 6.0, 5: 4.0, 6: 30.0}
    result = services.score_formation([1, 2, 3, 4, 5], [6], captain=1, vice=3, roles=roles, scores=scores)
    top = next(e for e in result["effective"] if e["role"] == "TOP")
    assert top["id"] == 1 and top["score"] == 0.0  # il panchinaro ADC non sostituisce un TOP
    assert result["doubled"] == 3 and result["bonus"] == 5.0
    none = services.score_formation([1, 2, 3, 4, 5], [], captain=1, vice=6, roles=roles, scores=scores)
    assert none["doubled"] is None and none["bonus"] == 0.0


# --------------------------------------------------------------------------- torneo simulato
@pytest.fixture
def worlds():
    edition = CompetitionEdition.objects.create(
        competition=Competition.objects.get(code="WORLDS"),
        year=2026,
        name="Worlds 2026",
        starts_at=day(15, 0),
        ends_at=day(15, 0) + timedelta(days=31),
        is_active=True,
    )
    stages = {s.code: s for s in ensure_worlds_stages(edition)}
    teams = {code: TeamFactory(name=f"Team {code}", acronym=code) for code in "ABCDP"}
    rosters = {}
    for index, (code, team) in enumerate(teams.items()):
        rosters[code] = [
            EditionRoster.objects.create(
                edition=edition,
                team=team,
                role=role,
                quotazione=8 + index + (2 if role == "MID" else 0),
                player=PlayerFactory(nickname=f"{code}-{role}"),
                active_from=edition.starts_at,
            )
            for role in ROLES
        ]
    t = teams
    schedule = [
        ("PLAY_IN", "P", "D", day(15), "D"),
        ("SWISS", "A", "B", day(20), "A"),
        ("SWISS", "C", "D", day(20, 11), "C"),
        ("SWISS", "A", "C", day(21), "A"),
        ("SWISS", "B", "D", day(21, 11), "B"),
        ("SWISS", "A", "D", day(22), "A"),
        ("SWISS", "B", "C", day(22, 11), "B"),
        ("SWISS", "B", "C", day(23), "C"),
        ("SWISS", "A", "C", day(24), "C"),
        ("QUARTERFINALS", "A", "B", day(30), "A"),
        ("QUARTERFINALS", "C", "P", day(30, 11), "C"),
        ("SEMIFINALS", "A", "C", day(6), "A"),
        ("FINAL", "A", "C", day(14), "A"),
    ]
    matches = []
    for stage, x, y, begin, winner in schedule:
        matches.append(
            add_match(
                edition,
                t[x],
                t[y],
                begin=begin,
                winner=t[winner],
                stage=stages[stage],
                status="not_started",
                stats_complete=False,
            )
        )
    owner, rival = UserFactory(username="owner"), UserFactory(username="rival")
    league = LeagueFactory(
        edition=edition,
        admin=owner,
        crediti_iniziali=100,
        settings={
            "budget": 100,
            "free_transfers_per_matchday": 2,
            "extra_transfer_penalty": 3,
            "captain_multiplier": 2,
            "max_participants": 50,
        },
    )
    mine = FantaTeamFactory(league=league, owner=owner, crediti_residui=100)
    theirs = FantaTeamFactory(league=league, owner=rival, crediti_residui=100)
    return {
        "edition": edition,
        "stages": stages,
        "teams": teams,
        "rosters": rosters,
        "matches": matches,
        "league": league,
        "mine": mine,
        "theirs": theirs,
        "owner": owner,
        "rival": rival,
    }


def player(ctx, code, role):
    return next(e for e in ctx["rosters"][code] if e.role == role).player_id


def play(match, ctx, lines=None):
    """Chiude la serie con un game: ogni player dei due team ha statistiche (salvo quelli esclusi)."""
    match.status = "finished"
    match.stats_complete = True
    match.save()
    game = add_game(match, 1, winner=match.winner_team)
    lines = lines or {}
    for entry in match.match_teams.all():
        code = entry.team.acronym
        for roster in ctx["rosters"][code]:
            k, d, a, cs, vs = lines.get(roster.player_id, (2, 1, 3, 200, 30))
            if k is None:
                continue
            add_stat(
                game,
                roster.player,
                kills=k,
                deaths=d,
                assists=a,
                cs=cs,
                vision=vs,
                win=entry.team_id == match.winner_team_id,
                team=entry.team,
            )
    return game


def buy(ctx, team, player_in, player_out=None, user=None):
    return services.make_transfer(user or team.owner, team.id, player_out, player_in)


def test_simulazione_torneo_worlds_end_to_end(worlds):
    ctx = worlds
    league, mine, theirs = ctx["league"], ctx["mine"], ctx["theirs"]
    with freeze_time(day(16)):
        matchdays.create(ctx["owner"], league_id=league.id, numero=None, descrizione=None, data=None)
        days = list(Matchday.objects.filter(league=league).order_by("numero"))
        assert [d.numero for d in days] == list(range(1, 9))
        assert [d.descrizione for d in days[:5]] == [f"Swiss Round {n}" for n in range(1, 6)]
        assert days[0].starts_at == day(20) and days[0].ends_at == day(21)
        assert days[3].starts_at == day(23) and days[4].starts_at == day(24)
        assert [d.stage.code for d in days[5:]] == ["QUARTERFINALS", "SEMIFINALS", "FINAL"]
        assert (
            league.fanta_teams.count() == 2 and Matchday.objects.get(pk=days[0].pk).league.participant_count
        )

        # Listone: prima della pubblicazione si compra solo dalle squadre qualificate direttamente.
        market = services.market(league)
        assert {i["team_sigla"] for i in market["items"]} == {"A", "B", "C"}
        with pytest.raises(BusinessRuleException, match="non è acquistabile"):
            buy(ctx, mine, player(ctx, "P", "TOP"))
        services.set_price(player(ctx, "A", "MID"), 20)
        services.publish_listone(ctx["edition"].id)
        with pytest.raises(BusinessRuleException, match="già pubblicato"):
            services.set_price(player(ctx, "A", "MID"), 19)
        assert {i["team_sigla"] for i in services.market(league)["items"]} == {"A", "B", "C", "D"}

        # Prima di G1: cambi illimitati e gratuiti, max 2 player per team, budget 100.
        squad = [
            ("A", "TOP"),
            ("A", "MID"),
            ("B", "JUNGLE"),
            ("B", "ADC"),
            ("C", "SUPPORT"),
            ("C", "MID"),
            ("D", "TOP"),
            ("D", "ADC"),
        ]
        for code, role in squad:
            buy(ctx, mine, player(ctx, code, role))
        assert all(t.is_free and t.penalty_points == 0 for t in Transfer.objects.filter(fanta_team=mine))
        assert mine.rosa.count() == 8
        cost = sum(
            EditionRoster.objects.get(edition=ctx["edition"], player_id=p).quotazione
            for p in mine.rosa.values_list("player_id", flat=True)
        )
        assert services.available_credits(mine) == 100 - cost
        with pytest.raises(BusinessRuleException, match="al massimo 8"):
            buy(ctx, mine, player(ctx, "B", "TOP"))
        buy(ctx, theirs, player(ctx, "A", "TOP"))
        buy(ctx, theirs, player(ctx, "A", "JUNGLE"))
        with pytest.raises(BusinessRuleException, match="al massimo 2 player dello stesso team"):
            buy(ctx, theirs, player(ctx, "A", "MID"))
        league.settings["budget"] = 30
        league.save()
        buy(ctx, theirs, player(ctx, "C", "MID"))
        with pytest.raises(BusinessRuleException, match="Crediti insufficienti"):
            buy(ctx, theirs, player(ctx, "B", "MID"))
        league.settings["budget"] = 100
        league.save()
        RosterEntry.objects.filter(fanta_team=theirs).delete()
        Transfer.objects.filter(fanta_team=theirs).delete()
        for code, role in [
            ("A", "TOP"),
            ("A", "ADC"),
            ("B", "MID"),
            ("B", "SUPPORT"),
            ("C", "JUNGLE"),
            ("C", "TOP"),
            ("D", "MID"),
            ("D", "SUPPORT"),
        ]:
            buy(ctx, theirs, player(ctx, code, role))

        # Formazione G1: 5 titolari, panchina ordinata, capitano e vice.
        starters = [
            player(ctx, "A", "TOP"),
            player(ctx, "B", "JUNGLE"),
            player(ctx, "A", "MID"),
            player(ctx, "B", "ADC"),
            player(ctx, "C", "SUPPORT"),
        ]
        bench = [player(ctx, "C", "MID"), player(ctx, "D", "TOP"), player(ctx, "D", "ADC")]
        with pytest.raises(BusinessRuleException, match="Capitano e vice"):
            services.save_lineup(
                ctx["owner"],
                mine,
                {
                    "titolari_ids": starters,
                    "panchina_ids": bench,
                    "capitano_id": starters[0],
                    "vice_capitano_id": starters[0],
                },
            )
        lineup = services.save_lineup(
            ctx["owner"],
            mine,
            {
                "titolari_ids": starters,
                "panchina_ids": bench,
                "capitano_id": player(ctx, "A", "MID"),
                "vice_capitano_id": player(ctx, "A", "TOP"),
            },
        )
        assert lineup["target_matchday_id"] == days[0].id and len(lineup["bench"]) == 3
        their_starters = [
            player(ctx, "A", "TOP"),
            player(ctx, "C", "JUNGLE"),
            player(ctx, "B", "MID"),
            player(ctx, "A", "ADC"),
            player(ctx, "B", "SUPPORT"),
        ]
        services.save_lineup(
            ctx["rival"],
            theirs,
            {
                "titolari_ids": their_starters,
                "panchina_ids": [],
                "capitano_id": their_starters[0],
                "vice_capitano_id": their_starters[1],
            },
        )

    # G1 (Swiss Round 1): il MID di A non gioca → subentra il MID di C; il capitano passa al vice.
    a_mid = player(ctx, "A", "MID")
    play(ctx["matches"][1], ctx, {a_mid: (None, 0, 0, 0, 0)})
    play(ctx["matches"][2], ctx)
    with freeze_time(day(21, 12)):
        matchdays.close(None, days[0].id)
    formation = Formation.objects.get(fanta_team=mine, matchday=days[0])
    base = {
        pid: game_score(r, 2, 1, 3, 200, 30, w)
        for pid, r, w in [
            (player(ctx, "A", "TOP"), "TOP", True),
            (player(ctx, "B", "JUNGLE"), "JUNGLE", False),
            (player(ctx, "C", "MID"), "MID", True),
            (player(ctx, "B", "ADC"), "ADC", False),
            (player(ctx, "C", "SUPPORT"), "SUPPORT", True),
        ]
    }
    expected = sum(base.values()) + base[player(ctx, "A", "TOP")]
    assert formation.punteggio_totale == pytest.approx(expected, abs=1e-9)
    subbed = next(e for e in formation.effective_titolari if e["role"] == "MID")
    assert subbed["id"] == player(ctx, "C", "MID") and subbed["substituted_for"] == a_mid
    assert formation.captain_points == pytest.approx(2 * base[player(ctx, "A", "TOP")])

    # G2: 2 cambi gratuiti, il terzo costa -3 punti.
    with freeze_time(day(20, 12)):
        summary = services.transfer_summary(mine)
        assert summary["target_matchday_numero"] == 2 and summary["free_transfers_remaining"] == 2
        buy(ctx, mine, player(ctx, "D", "MID"), player(ctx, "D", "TOP"))
        buy(ctx, mine, player(ctx, "D", "TOP"), player(ctx, "D", "MID"))
        third = buy(ctx, mine, player(ctx, "D", "MID"), player(ctx, "D", "TOP"))
        assert not third.is_free and third.penalty_points == 3
        assert services.transfer_summary(mine)["free_transfers_remaining"] == 0

    play(ctx["matches"][3], ctx)
    play(ctx["matches"][4], ctx)
    with freeze_time(day(22, 12)):
        matchdays.close(None, days[1].id)
    assert Formation.objects.get(fanta_team=mine, matchday=days[1]).penalty_points == 3
    play(ctx["matches"][5], ctx)
    play(ctx["matches"][6], ctx)
    with freeze_time(day(23, 2)):
        matchdays.close(None, days[2].id)
        # D ha perso 3 serie Swiss: vendere un suo player è sempre gratuito e non consuma la quota.
        assert ctx["teams"]["D"].id in services.eliminated_teams(ctx["edition"])
        freed = buy(ctx, mine, player(ctx, "D", "SUPPORT"), player(ctx, "D", "ADC"))
        assert freed.is_free and freed.freed_by_elimination
        assert services.transfer_summary(mine)["free_transfers_remaining"] == 2

    for match in ctx["matches"][7:9]:
        play(match, ctx)
    with freeze_time(day(25)):
        matchdays.close(None, days[3].id)
        matchdays.close(None, days[4].id)
        # Prima dei quarti: cambi illimitati, budget 105, massimo 3 player per team.
        summary = services.transfer_summary(mine)
        assert summary["unlimited"] and summary["budget"] == 105 and summary["max_players_per_team"] == 3
        credits_before = services.available_credits(mine)
        assert credits_before == services.budget(league) - sum(
            EditionRoster.objects.get(edition=ctx["edition"], player_id=p).quotazione
            for p in mine.rosa.values_list("player_id", flat=True)
        )
        buy(ctx, mine, player(ctx, "A", "JUNGLE"), player(ctx, "C", "MID"))
        assert Transfer.objects.filter(fanta_team=mine).last().is_free

    for match in ctx["matches"][9:]:
        play(match, ctx)
    for index, moment in ((5, day(31)), (6, day(7)), (7, day(15))):
        with freeze_time(moment):
            matchdays.close(None, days[index].id)
    ranking = services.ranking(league)
    assert len(ranking) == 2 and all(len(row["matchdays"]) == 8 for row in ranking)
    mine.refresh_from_db()
    assert mine.punti == pytest.approx(
        next(r["overall_total"] for r in ranking if r["fantasy_team_id"] == mine.id)
    )


def test_spareggi_della_classifica_worlds(worlds):
    ctx = worlds
    third = FantaTeamFactory(league=ctx["league"])
    days = [
        Matchday.objects.create(league=ctx["league"], numero=n, chiusa=True, provisional=False)
        for n in (1, 2)
    ]
    totals = {ctx["mine"]: [(10, 4), (10, 4)], ctx["theirs"]: [(15, 2), (5, 2)], third: [(15, 6), (5, 6)]}
    for team, values in totals.items():
        for matchday, (points, captain) in zip(days, values, strict=True):
            Formation.objects.create(
                fanta_team=team, matchday=matchday, punteggio_totale=points, captain_points=captain
            )
    ranking = services.ranking(ctx["league"])
    # Tutti a 20: miglior giornata (15 > 10), poi totale capitani (12 > 4), poi data di iscrizione.
    assert [r["fantasy_team_id"] for r in ranking] == [third.id, ctx["theirs"].id, ctx["mine"].id]


def test_quotazioni_automatiche_dalla_stagione_regionale(worlds):
    ctx = worlds
    lck = CompetitionEdition.objects.create(
        competition=Competition.objects.get(code="LCK"),
        year=2026,
        name="LCK 2026",
        starts_at=day(15) - timedelta(days=90),
    )
    a, b = ctx["teams"]["A"], ctx["teams"]["B"]
    for code, team in (("A", a), ("B", b)):
        for entry in ctx["rosters"][code]:
            EditionRoster.objects.create(
                edition=lck, team=team, player=entry.player, role=entry.role, active_from=lck.starts_at
            )
    match = add_match(lck, a, b, begin=day(15) - timedelta(days=30), winner=a)
    game = add_game(match)
    add_stat(game, ctx["rosters"]["A"][2].player, kills=10, assists=10, cs=400, win=True)
    add_stat(game, ctx["rosters"]["B"][2].player, kills=0, deaths=5, cs=100)
    a_top = EditionRoster.objects.get(edition=ctx["edition"], player=ctx["rosters"]["A"][0].player)
    a_top.quotazione, a_top.quotazione_set_by_admin = 17, True
    a_top.save()
    report = pricing.compute_prices(ctx["edition"])
    assert report["priced"] == 2 and report["kept_admin"] == 1
    price = {e.player.nickname: e.quotazione for e in EditionRoster.objects.filter(edition=ctx["edition"])}
    assert price["A-MID"] == 20 and price["B-MID"] == 5 and price["C-MID"] == 12  # mediana del ruolo
    assert price["A-TOP"] == 17
    call_command("compute_worlds_prices", edition=ctx["edition"].id, force=True)
    assert EditionRoster.objects.get(pk=a_top.pk).quotazione == 12
    assert pricing.scale(5, 5, 5) == 12


@freeze_time("2026-10-16T08:00:00Z")
def test_api_worlds(worlds):
    ctx = worlds
    owner = auth_client(ctx["owner"])
    market = owner.get(f"/api/worlds/leagues/{ctx['league'].id}/market")
    assert market.status_code == 200 and market.json()["budget"] == 100
    services.generate_matchdays(ctx["league"])
    created = owner.post(
        f"/api/worlds/fanta-teams/{ctx['mine'].id}/transfers",
        {"playerInId": player(ctx, "A", "TOP")},
        format="json",
    )
    assert created.status_code == 201 and created.json()["playerInNickname"] == "A-TOP"
    summary = owner.get(f"/api/worlds/fanta-teams/{ctx['mine'].id}/transfers").json()
    assert summary["items"][0]["priceIn"] == created.json()["priceIn"]
    assert auth_client(UserFactory()).get(f"/api/worlds/leagues/{ctx['league'].id}/market").status_code == 403
    admin = auth_client(UserFactory(role="ADMIN"))
    price = admin.put(
        f"/api/admin/worlds/players/{player(ctx, 'B', 'TOP')}/price", {"quotazione": 18}, format="json"
    )
    assert price.status_code == 200 and price.json()["quotazione"] == 18
    assert (
        admin.put(
            f"/api/admin/worlds/players/{player(ctx, 'B', 'TOP')}/price", {"quotazione": 30}, format="json"
        ).status_code
        == 422
    )
    published = admin.post(f"/api/admin/worlds/editions/{ctx['edition'].id}/publish-listone")
    assert published.status_code == 200 and published.json()["listonePublishedAt"]
    assert owner.post(f"/api/admin/worlds/editions/{ctx['edition'].id}/publish-listone").status_code == 403
    ranking = owner.get(f"/api/leagues/{ctx['league'].id}/cumulative-ranking").json()
    assert ranking["ruleset"] == "WORLDS" and len(ranking["items"]) == 2
    regional = LeagueFactory()
    assert auth_client(regional.admin).get(f"/api/worlds/leagues/{regional.id}/market").status_code == 422


def test_regole_di_mercato_e_lega_worlds_senza_asta(worlds):
    ctx = worlds
    with pytest.raises(BusinessRuleException, match="non prevedono l'asta"):
        from apps.leagues.services import open_auction

        open_auction(ctx["owner"], ctx["league"].id)
    with pytest.raises(BusinessRuleException, match="Indica il player"):
        services.make_transfer(ctx["owner"], ctx["mine"].id, None, None)
    with pytest.raises(BusinessRuleException, match="non è nella tua rosa"):
        services.make_transfer(ctx["owner"], ctx["mine"].id, player(ctx, "A", "TOP"), None)
    stage = Stage.objects.get(edition=ctx["edition"], code="SWISS")
    assert stage.max_players_per_team == 2 and stage.free_transfers_unlimited_before
    with pytest.raises(BusinessRuleException, match="publicare|pubblicare"):
        CompetitionEdition.objects.filter(pk=ctx["edition"].pk)
        from apps.esports.models import EsportsMatch

        EsportsMatch.objects.filter(stage__code="SWISS").update(stage=None)
        services.publish_listone(ctx["edition"].id)


@freeze_time("2026-10-16T08:00:00Z")
def test_formazione_worlds_via_api_lineup(worlds):
    ctx = worlds
    services.generate_matchdays(ctx["league"])
    for code, role in [
        ("A", "TOP"),
        ("A", "MID"),
        ("B", "JUNGLE"),
        ("B", "ADC"),
        ("C", "SUPPORT"),
        ("C", "MID"),
    ]:
        buy(ctx, ctx["mine"], player(ctx, code, role))
    owner = auth_client(ctx["owner"])
    url = f"/api/fanta-teams/{ctx['mine'].id}/formazioni/lineup"
    starters = [
        player(ctx, "A", "TOP"),
        player(ctx, "B", "JUNGLE"),
        player(ctx, "A", "MID"),
        player(ctx, "B", "ADC"),
        player(ctx, "C", "SUPPORT"),
    ]
    response = owner.put(
        url,
        {
            "titolariIds": starters,
            "panchinaIds": [player(ctx, "C", "MID")],
            "capitanoId": starters[2],
            "viceCapitanoId": starters[0],
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capitanoId"] == starters[2] and [b["id"] for b in body["bench"]] == [player(ctx, "C", "MID")]
    assert body["targetMatchdayId"] and body["lockAt"]
    assert owner.get(url).json()["viceCapitanoId"] == starters[0]
    history = owner.get(f"/api/fanta-teams/{ctx['mine'].id}/formazioni").json()
    assert history[0]["capitanoId"] == starters[2]
