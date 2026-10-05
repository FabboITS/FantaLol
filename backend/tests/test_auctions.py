"""Porting di AuctionServiceTest + concorrenza (rilanci simultanei con select_for_update)."""

import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone
from freezegun import freeze_time

from apps.common.exceptions import BusinessRuleException
from apps.leagues import auctions
from apps.leagues.models import AuctionSession, AuctionStatus, FantaTeam, RosterEntry

from .conftest import auth_client
from .factories import EditionFactory, FantaTeamFactory, LeagueFactory, UserFactory, build_edition_rosters


@pytest.fixture
def setup(db):
    edition = EditionFactory()
    entries = [e for team in build_edition_rosters(edition, 10).values() for e in team]
    owner, rival = UserFactory(username="owner"), UserFactory(username="rival")
    league = LeagueFactory(edition=edition, participant_count=2, auction_open=True)
    mine = FantaTeamFactory(league=league, owner=owner, crediti_residui=1000)
    theirs = FantaTeamFactory(league=league, owner=rival, crediti_residui=1000)
    return {
        "league": league,
        "entries": entries,
        "owner": owner,
        "rival": rival,
        "mine": mine,
        "theirs": theirs,
    }


def test_nomina_e_rilancio_rifiutati_ad_asta_della_lega_chiusa(setup):
    league = setup["league"]
    auction = auctions.start(setup["owner"], league.id, setup["entries"][0].player_id, setup["mine"].id)
    league.auction_open = False
    league.save()
    with pytest.raises(BusinessRuleException, match="L'asta della lega non è aperta"):
        auctions.start(setup["owner"], league.id, setup["entries"][1].player_id, setup["mine"].id)
    with pytest.raises(BusinessRuleException, match="L'asta della lega non è aperta"):
        auctions.bid(setup["rival"], auction.id, setup["theirs"].id, 20)


def test_nomina_con_scadenza_a_quindici_secondi(setup):
    before = timezone.now()
    auction = auctions.start(
        setup["owner"], setup["league"].id, setup["entries"][0].player_id, setup["mine"].id
    )
    after = timezone.now()
    assert before + timedelta(seconds=15) <= auction.ends_at <= after + timedelta(seconds=15)
    assert auction.current_bid == setup["entries"][0].quotazione and auction.highest_bidder == setup["mine"]
    with pytest.raises(BusinessRuleException, match="C'è già un'asta attiva in questa lega"):
        auctions.start(setup["rival"], setup["league"].id, setup["entries"][1].player_id, setup["theirs"].id)


def test_rilancio_valido_riavvia_il_timer(setup):
    auction = auctions.start(
        setup["owner"], setup["league"].id, setup["entries"][0].player_id, setup["mine"].id
    )
    before = timezone.now()
    result = auctions.bid(setup["rival"], auction.id, setup["theirs"].id, auction.current_bid + 1)
    assert result.ends_at >= before + timedelta(seconds=15)
    with pytest.raises(BusinessRuleException, match="Sei già il miglior offerente"):
        auctions.bid(setup["rival"], auction.id, setup["theirs"].id, 500)
    with pytest.raises(BusinessRuleException, match="L'offerta minima è"):
        auctions.bid(setup["owner"], auction.id, setup["mine"].id, result.current_bid)
    with pytest.raises(BusinessRuleException, match="Non puoi offrire per questa squadra"):
        auctions.bid(setup["owner"], auction.id, setup["theirs"].id, 900)


def test_offerta_di_tutti_i_crediti_e_rilancio_successivo_rifiutato(setup):
    auction = auctions.start(
        setup["owner"], setup["league"].id, setup["entries"][0].player_id, setup["mine"].id
    )
    assert auctions.bid(setup["rival"], auction.id, setup["theirs"].id, 1000).current_bid == 1000
    with pytest.raises(BusinessRuleException, match="Crediti insufficienti"):
        auctions.bid(setup["owner"], auction.id, setup["mine"].id, 1001)


def test_finalizzazione_allo_scadere_assegna_il_player_e_scala_i_crediti(setup):
    entry = setup["entries"][0]
    auction = auctions.start(setup["owner"], setup["league"].id, entry.player_id, setup["mine"].id)
    auctions.bid(setup["rival"], auction.id, setup["theirs"].id, 77)
    with freeze_time(timezone.now() + timedelta(seconds=16)):
        assert auctions.finalize_expired() == 1
    auction.refresh_from_db()
    setup["theirs"].refresh_from_db()
    assert auction.status == AuctionStatus.WON and setup["theirs"].crediti_residui == 923
    assert RosterEntry.objects.get(player_id=entry.player_id).fanta_team == setup["theirs"]


def test_finalizzazione_pigra_su_lettura_e_su_rilancio(setup):
    auction = auctions.start(
        setup["owner"], setup["league"].id, setup["entries"][0].player_id, setup["mine"].id
    )
    with freeze_time(timezone.now() + timedelta(seconds=20)):
        with pytest.raises(BusinessRuleException, match="L'asta è terminata"):
            auctions.bid_or_finalize(setup["rival"], auction.id, setup["theirs"].id, 50)
        auction.refresh_from_db()
        assert auction.status == AuctionStatus.WON
    second = auctions.start(
        setup["owner"], setup["league"].id, setup["entries"][1].player_id, setup["mine"].id
    )
    with freeze_time(timezone.now() + timedelta(seconds=20)):
        assert auctions.active(setup["league"].id) is None
    second.refresh_from_db()
    assert second.status == AuctionStatus.WON


def test_vincoli_di_rosa_per_ruolo(setup):
    league = setup["league"]
    mids = [e for e in setup["entries"] if e.role == "MID"][:3]
    for entry in mids[:2]:
        RosterEntry.objects.create(
            fanta_team=setup["mine"], league=league, player=entry.player, crediti_spesi=1
        )
    with pytest.raises(BusinessRuleException, match="limite per il ruolo MID"):
        auctions.start(setup["owner"], league.id, mids[2].player_id, setup["mine"].id)
    with pytest.raises(BusinessRuleException, match="già assegnato"):
        auctions.start(setup["rival"], league.id, mids[0].player_id, setup["theirs"].id)


def test_api_aste(setup):
    client = auth_client(setup["owner"])
    league, entry = setup["league"], setup["entries"][0]
    started = client.post(
        "/api/auctions",
        {"leagueId": league.id, "lecPlayerId": entry.player_id, "fantaTeamId": setup["mine"].id},
        format="json",
    )
    assert started.status_code == 201
    body = started.json()
    assert set(body) >= {
        "id",
        "leagueId",
        "lecPlayerId",
        "playerNickname",
        "playerRole",
        "currentBid",
        "highestBidderId",
        "highestBidderName",
        "endsAt",
        "status",
    }
    assert client.get(f"/api/auctions/active?leagueId={league.id}").json()["id"] == body["id"]
    rival = auth_client(setup["rival"]).post(
        f"/api/auctions/{body['id']}/bids", {"fantaTeamId": setup["theirs"].id, "credits": 50}, format="json"
    )
    assert rival.status_code == 200 and rival.json()["highestBidderName"] == setup["theirs"].nome
    assert client.get("/api/auctions/active").status_code == 400


@pytest.mark.django_db(transaction=True)
def test_due_rilanci_simultanei_un_solo_vincitore_e_crediti_mai_negativi():
    edition = EditionFactory()
    entries = [e for team in build_edition_rosters(edition, 10).values() for e in team]
    league = LeagueFactory(edition=edition, participant_count=3, auction_open=True)
    opener = FantaTeamFactory(league=league, crediti_residui=1000)
    bidders = [FantaTeamFactory(league=league, crediti_residui=60) for _ in range(2)]
    auction = auctions.start(opener.owner, league.id, entries[0].player_id, opener.id)
    barrier = threading.Barrier(2)
    results: list = []

    def place(team):
        try:
            barrier.wait()
            auctions.bid(team.owner, auction.id, team.id, 60)
            results.append(("ok", team.id))
        except BusinessRuleException as error:
            results.append(("ko", str(error)))
        finally:
            connection.close()

    threads = [threading.Thread(target=place, args=(team,)) for team in bidders]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(r[0] for r in results) == ["ko", "ok"]
    assert any("L'offerta minima è 61 crediti" in r[1] for r in results if r[0] == "ko")
    winner_id = next(r[1] for r in results if r[0] == "ok")
    AuctionSession.objects.filter(pk=auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
    auctions.finalize_expired()
    assert RosterEntry.objects.get(player_id=entries[0].player_id).fanta_team_id == winner_id
    assert all(team.crediti_residui >= 0 for team in FantaTeam.objects.all())
    assert FantaTeam.objects.get(pk=winner_id).crediti_residui == 0
