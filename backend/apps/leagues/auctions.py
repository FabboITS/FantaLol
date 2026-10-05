"""Asta a rilancio con countdown (porting di ``AuctionService``).

La concorrenza è gestita con ``select_for_update()`` su lega, asta, player e FantaTeam dentro
``transaction.atomic()``. Le aste scadute sono finalizzate dallo sweeper dello scheduler (ogni secondo)
e, in modo "pigro", quando si legge o si rilancia su un'asta scaduta.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException
from apps.common.utils import now
from apps.users.models import User

from . import policy
from .models import AuctionSession, AuctionStatus, FantaTeam, League, RosterEntry
from .services import active_roster_entry, edition_roster_map, get_league_for_update, is_global_admin


def auction_response(auction: AuctionSession | None) -> dict | None:
    if auction is None:
        return None
    info = active_roster_entry(auction.league.edition_id, auction.player_id)
    return {
        "id": auction.id,
        "league_id": auction.league_id,
        "lec_player_id": auction.player_id,
        "player_nickname": auction.player.nickname,
        "player_role": info.role if info else None,
        "current_bid": auction.current_bid,
        "highest_bidder_id": auction.highest_bidder_id,
        "highest_bidder_name": auction.highest_bidder.nome if auction.highest_bidder else None,
        "ends_at": auction.ends_at,
        "status": auction.status,
    }


def _deadline():
    return now() + timedelta(seconds=settings.AUCTION_SECONDS_PER_BID)


def _validate_roster_slot(team: FantaTeam, player_id: int, role: str | None) -> None:
    entries = list(team.rosa.all())
    limits = policy.roster_limits(team.league)
    if len(entries) >= limits.max_roster_size:
        raise BusinessRuleException("Rosa già completa")
    roster = edition_roster_map(team.league.edition_id, [e.player_id for e in entries])
    same_role = sum(1 for e in entries if e.player_id in roster and roster[e.player_id].role == role)
    if limits.max_per_role is not None and same_role >= limits.max_per_role:
        raise BusinessRuleException(f"Hai già raggiunto il limite per il ruolo {role}")


def _assert_auction_open(league: League) -> None:
    if not league.auction_open:
        raise BusinessRuleException("L'asta della lega non è aperta")


def _assert_owner_or_admin(user: User, team: FantaTeam) -> None:
    if team.owner_id != user.id and not is_global_admin(user):
        raise BusinessRuleException("Non puoi offrire per questa squadra")


def _team_in_league(team_id: int, league: League) -> FantaTeam:
    team = FantaTeam.objects.select_for_update().select_related("league__edition").filter(pk=team_id).first()
    if team is None:
        raise ResourceNotFoundException("FantaTeam non trovata")
    if team.league_id != league.id:
        raise BusinessRuleException("La squadra non partecipa a questa lega")
    return team


@transaction.atomic
def start(user: User, league_id: int, player_id: int, team_id: int) -> AuctionSession:
    league = get_league_for_update(league_id)
    _assert_auction_open(league)
    if not is_global_admin(user) and not league.fanta_teams.filter(owner=user).exists():
        raise BusinessRuleException("Non partecipi a questa lega")
    existing = (
        AuctionSession.objects.select_for_update().filter(league=league, status=AuctionStatus.ACTIVE).first()
    )
    if existing is not None:
        if existing.ends_at > now():
            raise BusinessRuleException("C'è già un'asta attiva in questa lega")
        _finalize(existing)
    info = active_roster_entry(league.edition_id, player_id)
    if info is None or info.active_to is not None:
        raise ResourceNotFoundException("Player non trovato")
    player = info.player.__class__.objects.select_for_update().get(pk=player_id)
    if RosterEntry.objects.filter(league=league, player_id=player_id).exists():
        raise BusinessRuleException("Questo player è già assegnato nella lega")
    team = _team_in_league(team_id, league)
    _assert_owner_or_admin(user, team)
    _validate_roster_slot(team, player_id, info.role)
    if team.crediti_residui < info.quotazione:
        raise BusinessRuleException("Crediti insufficienti per avviare l'asta")
    return AuctionSession.objects.create(
        league=league,
        player=player,
        current_bid=info.quotazione,
        highest_bidder=team,
        ends_at=_deadline(),
        status=AuctionStatus.ACTIVE,
    )


@transaction.atomic
def bid(user: User, auction_id: int, team_id: int, credits: int) -> AuctionSession:
    auction = (
        AuctionSession.objects.select_for_update()
        .select_related("league__edition", "player")
        .filter(pk=auction_id)
        .first()
    )
    if auction is None:
        raise ResourceNotFoundException("Asta non trovata")
    _assert_auction_open(auction.league)
    if auction.status != AuctionStatus.ACTIVE or auction.ends_at <= now():
        # Il rollback annulla questa transazione: la finalizzazione avviene in bid_or_finalize.
        raise _AuctionEnded()
    team = _team_in_league(team_id, auction.league)
    _assert_owner_or_admin(user, team)
    if auction.highest_bidder_id == team.id:
        raise BusinessRuleException("Sei già il miglior offerente")
    minimum = auction.current_bid if auction.highest_bidder_id is None else auction.current_bid + 1
    if credits < minimum:
        raise BusinessRuleException(f"L'offerta minima è {minimum} crediti")
    if credits > team.crediti_residui:
        raise BusinessRuleException("Crediti insufficienti")
    info = active_roster_entry(auction.league.edition_id, auction.player_id)
    _validate_roster_slot(team, auction.player_id, info.role if info else None)
    auction.highest_bidder = team
    auction.current_bid = credits
    auction.ends_at = _deadline()
    auction.save(update_fields=["highest_bidder", "current_bid", "ends_at"])
    return auction


class _AuctionEnded(BusinessRuleException):
    def __init__(self):
        super().__init__("L'asta è terminata")


def bid_or_finalize(user: User, auction_id: int, team_id: int, credits: int) -> AuctionSession:
    """Rilancio; se l'asta è scaduta la finalizza (in una transazione separata) e segnala l'errore."""
    try:
        return bid(user, auction_id, team_id, credits)
    except _AuctionEnded:
        finalize_by_id(auction_id)
        raise BusinessRuleException("L'asta è terminata")


def active(league_id: int) -> AuctionSession | None:
    auction = (
        AuctionSession.objects.select_related("league__edition", "player", "highest_bidder")
        .filter(league_id=league_id, status=AuctionStatus.ACTIVE)
        .first()
    )
    if auction is not None and auction.ends_at <= now():
        finalize_by_id(auction.id)
        return None
    return auction


@transaction.atomic
def finalize_by_id(auction_id: int) -> None:
    auction = AuctionSession.objects.select_for_update().filter(pk=auction_id).first()
    if auction is not None:
        _finalize(auction)


def finalize_expired() -> int:
    """Sweeper: finalizza tutte le aste scadute (usato dallo scheduler ogni secondo)."""
    count = 0
    ids = list(
        AuctionSession.objects.filter(status=AuctionStatus.ACTIVE, ends_at__lte=now()).values_list(
            "id", flat=True
        )
    )
    for auction_id in ids:
        with transaction.atomic():
            auction = AuctionSession.objects.select_for_update(skip_locked=True).filter(pk=auction_id).first()
            if auction is not None:
                _finalize(auction)
                count += 1
    return count


def _finalize(auction: AuctionSession) -> None:
    if auction.status != AuctionStatus.ACTIVE:
        return
    winner = None
    if auction.highest_bidder_id is not None:
        winner = (
            FantaTeam.objects.select_for_update()
            .select_related("league__edition")
            .get(pk=auction.highest_bidder_id)
        )
    already_taken = RosterEntry.objects.filter(
        league_id=auction.league_id, player_id=auction.player_id
    ).exists()
    if winner is None or winner.crediti_residui < auction.current_bid or already_taken:
        auction.status = AuctionStatus.EXPIRED
    else:
        try:
            info = active_roster_entry(winner.league.edition_id, auction.player_id)
            _validate_roster_slot(winner, auction.player_id, info.role if info else None)
        except BusinessRuleException:
            auction.status = AuctionStatus.EXPIRED
        else:
            winner.crediti_residui -= auction.current_bid
            winner.save(update_fields=["crediti_residui"])
            RosterEntry.objects.create(
                fanta_team=winner,
                league_id=auction.league_id,
                player_id=auction.player_id,
                crediti_spesi=auction.current_bid,
            )
            auction.status = AuctionStatus.WON
    auction.save(update_fields=["status"])
    if auction.status == AuctionStatus.WON:
        from apps.lineups.services import ensure_fixed_roster_periods

        ensure_fixed_roster_periods(winner)
