"""Regole di business di leghe, rose e asta.

Porting diretto di `LeagueService`, `FantaTeamService` e `AuctionService`.
I messaggi d'errore restano in italiano e identici all'originale, perché il
frontend li mostra così come sono.
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.exceptions import AccessDenied, BusinessRuleError, ResourceNotFound
from teams.models import ROLE_ORDER, ProPlayer

from .models import AuctionSession, AuctionStatus, FantaTeam, League, LeagueStatus, RosterEntry

MAX_TEAMS_PER_LEAGUE = settings.FANTALOL["MAX_TEAMS_PER_LEAGUE"]
SECONDS_PER_BID = settings.FANTALOL["AUCTION_SECONDS_PER_BID"]


# --------------------------------------------------------------------------
# Lookup e autorizzazioni
# --------------------------------------------------------------------------
def get_league_or_404(league_id) -> League:
    try:
        return League.objects.get(pk=league_id)
    except League.DoesNotExist as exc:
        raise ResourceNotFound(f"Lega non trovata con id: {league_id}") from exc


def get_league_for_update(league_id) -> League:
    league = League.objects.select_for_update().filter(pk=league_id).first()
    if league is None:
        raise ResourceNotFound(f"Lega non trovata con id: {league_id}")
    return league


def get_league_by_invite_code(codice_invito: str) -> League:
    league = League.objects.filter(codice_invito=codice_invito).first()
    if league is None:
        raise BusinessRuleError(f"Nessuna lega trovata con codice invito: {codice_invito}")
    return league


def get_fanta_team_or_404(team_id) -> FantaTeam:
    try:
        return FantaTeam.objects.select_related("league", "owner").get(pk=team_id)
    except FantaTeam.DoesNotExist as exc:
        raise ResourceNotFound(f"FantaTeam non trovata con id: {team_id}") from exc


def assert_can_view_league(user, league: League) -> None:
    if user.is_global_admin:
        return
    if league.admin_id == user.id:
        return
    if FantaTeam.objects.filter(league=league, owner=user).exists():
        return
    raise AccessDenied("You cannot access this league")


def assert_league_creator_or_admin(user, league: League) -> None:
    if not user.is_global_admin and league.admin_id != user.id:
        raise BusinessRuleError("Solo il creatore della lega può gestire l'asta")


def assert_team_owner(user, team: FantaTeam) -> None:
    if team.owner_id != user.id and not user.is_global_admin:
        raise BusinessRuleError("Non sei il proprietario di questa squadra fantacalcistica")


# --------------------------------------------------------------------------
# Leghe
# --------------------------------------------------------------------------
def visible_leagues(user):
    """Le leghe che l'utente amministra o a cui partecipa (tutte, se ADMIN)."""
    if user.is_global_admin:
        return League.objects.all().order_by("id")
    return (League.objects
            .filter(Q(admin=user) | Q(fanta_teams__owner=user))
            .distinct()
            .order_by("id"))


@transaction.atomic
def create_league(user, nome: str, crediti_iniziali: int | None, competition: str | None) -> League:
    return League.objects.create(
        nome=nome,
        crediti_iniziali=crediti_iniziali or settings.FANTALOL["DEFAULT_LEAGUE_CREDITS"],
        admin=user,
        competition=competition or "LEC",
    )


@transaction.atomic
def delete_league(user, league_id) -> None:
    league = get_league_or_404(league_id)
    if not user.is_global_admin and league.admin_id != user.id:
        raise AccessDenied("You cannot delete this league")
    league.delete()


@transaction.atomic
def open_auction(user, league_id) -> League:
    league = get_league_for_update(league_id)
    assert_league_creator_or_admin(user, league)
    if not league.competition_started:
        raise BusinessRuleError("Crea una giornata prima di aprire l'asta")
    league.auction_open = True
    league.status = LeagueStatus.AUCTION_OPEN
    league.save(update_fields=["auction_open", "status"])
    return league


@transaction.atomic
def close_auction(user, league_id) -> League:
    league = get_league_for_update(league_id)
    assert_league_creator_or_admin(user, league)
    if AuctionSession.objects.filter(league=league, status=AuctionStatus.ACTIVE).exists():
        raise BusinessRuleError(
            "Attendi la fine dell'asta del player prima di terminare l'asta della lega")
    league.auction_open = False
    league.status = LeagueStatus.AUCTION_CLOSED
    league.save(update_fields=["auction_open", "status"])
    return league


@transaction.atomic
def start_competition_and_open_auction(league: League) -> League:
    """Chiamata alla creazione della prima giornata: congela i partecipanti."""
    league.freeze_participant_count(league.fanta_teams.count())
    league.auction_open = True
    league.status = LeagueStatus.AUCTION_OPEN
    league.save(update_fields=["participant_count", "auction_open", "status"])
    return league


@transaction.atomic
def complete_all_rosters_randomly(user, league_id) -> list[FantaTeam]:
    """Completa casualmente le rose incomplete, rispettando i limiti per ruolo."""
    league = get_league_for_update(league_id)
    assert_league_creator_or_admin(user, league)
    if league.auction_open:
        raise BusinessRuleError("Termina l'asta della lega prima di completare casualmente le rose")

    max_size, max_per_role = league.roster_limits
    teams = list(league.fanta_teams.all().order_by("id"))
    taken = set(RosterEntry.objects.filter(fanta_team__league=league).values_list("player_id", flat=True))
    available = [p for p in ProPlayer.objects.filter(competition=league.competition)
                 if p.id not in taken]
    random.shuffle(available)

    by_role: dict[str, list[ProPlayer]] = {role.value: [] for role in ROLE_ORDER}
    for player in available:
        by_role.setdefault(player.ruolo, []).append(player)

    assignments: list[tuple[FantaTeam, list[ProPlayer]]] = []
    for team in teams:
        current = list(team.rosa.select_related("player").all())
        if len(current) >= max_size:
            continue
        counts: dict[str, int] = {}
        for entry in current:
            counts[entry.player.ruolo] = counts.get(entry.player.ruolo, 0) + 1
        selected: list[ProPlayer] = []
        for role in ROLE_ORDER:
            missing = max_per_role - counts.get(role.value, 0)
            pool = by_role.setdefault(role.value, [])
            if len(pool) < missing:
                raise BusinessRuleError(
                    "Non ci sono abbastanza player disponibili per completare tutte le rose")
            for _ in range(missing):
                selected.append(pool.pop())
        assignments.append((team, selected))

    assigned_ids: set[int] = set()
    for team, players in assignments:
        for player in players:
            if player.id in assigned_ids:
                raise BusinessRuleError("Un player casuale è stato selezionato più volte")
            assigned_ids.add(player.id)
            RosterEntry.objects.create(fanta_team=team, player=player, crediti_spesi=0)
    return teams


# --------------------------------------------------------------------------
# FantaTeam e rose
# --------------------------------------------------------------------------
@transaction.atomic
def join_league(user, codice_invito: str, nome_squadra: str) -> FantaTeam:
    league = get_league_by_invite_code(codice_invito)
    if league.competition_started:
        raise BusinessRuleError("La lega è già iniziata: non è più possibile iscriversi")
    if league.fanta_teams.count() >= MAX_TEAMS_PER_LEAGUE:
        raise BusinessRuleError(f"La lega ha già raggiunto il limite di {MAX_TEAMS_PER_LEAGUE} squadre")
    if FantaTeam.objects.filter(league=league, owner=user).exists():
        raise BusinessRuleError("Sei già iscritto a questa lega con una squadra")
    return FantaTeam.objects.create(
        nome=nome_squadra,
        crediti_residui=league.crediti_iniziali,
        league=league,
        owner=user,
    )


def roster_counts_by_role(team: FantaTeam) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in team.rosa.select_related("player").all():
        counts[entry.player.ruolo] = counts.get(entry.player.ruolo, 0) + 1
    return counts


def validate_roster_slot(team: FantaTeam, player: ProPlayer) -> None:
    """Rosa non piena e limite per ruolo non superato."""
    max_size, max_per_role = team.league.roster_limits
    roster_size = team.rosa.count()
    if roster_size >= max_size:
        raise BusinessRuleError("Rosa già completa")
    if roster_counts_by_role(team).get(player.ruolo, 0) >= max_per_role:
        raise BusinessRuleError(f"Hai già raggiunto il limite per il ruolo {player.ruolo}")


def player_taken_in_league(league_id, player_id) -> bool:
    return RosterEntry.objects.filter(fanta_team__league_id=league_id, player_id=player_id).exists()


@transaction.atomic
def acquista_player(user, team_id, player_id: int, crediti_offerti: int) -> RosterEntry:
    team = get_fanta_team_or_404(team_id)
    assert_team_owner(user, team)
    player = ProPlayer.objects.select_for_update().filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFound(f"Player non trovato con id: {player_id}")

    if player_taken_in_league(team.league_id, player.id):
        raise BusinessRuleError(f"Il player {player.nickname} è già stato acquistato in questa lega")
    if crediti_offerti > team.crediti_residui:
        raise BusinessRuleError(
            f"Crediti insufficienti: residui {team.crediti_residui}, offerti {crediti_offerti}")
    if crediti_offerti < player.quotazione:
        raise BusinessRuleError(
            f"L'offerta ({crediti_offerti}) è inferiore alla quotazione base del player ({player.quotazione})")

    max_size, max_per_role = team.league.roster_limits
    if team.rosa.count() >= max_size:
        raise BusinessRuleError(f"Rosa al completo: massimo {max_size} player")
    if roster_counts_by_role(team).get(player.ruolo, 0) >= max_per_role:
        raise BusinessRuleError(
            f"Hai già raggiunto il numero massimo di player per il ruolo {player.ruolo}")

    team.crediti_residui -= crediti_offerti
    team.save(update_fields=["crediti_residui"])
    return RosterEntry.objects.create(fanta_team=team, player=player, crediti_spesi=crediti_offerti)


@transaction.atomic
def acquista_player_gratis(user, team_id) -> RosterEntry:
    """Player gratuito quando la squadra non può più permettersi nessuno."""
    team = get_fanta_team_or_404(team_id)
    assert_team_owner(user, team)
    max_size, max_per_role = team.league.roster_limits
    if team.rosa.count() >= max_size:
        raise BusinessRuleError("La rosa è già completa")

    altre_complete = all(
        other.rosa.count() >= max_size
        for other in team.league.fanta_teams.exclude(pk=team.pk)
    )
    if not altre_complete:
        raise BusinessRuleError(
            "Il player gratis è disponibile solo quando tutte le altre squadre hanno completato la rosa")

    counts = roster_counts_by_role(team)
    candidates = [
        p for p in ProPlayer.objects.filter(competition=team.league.competition).order_by("quotazione", "id")
        if counts.get(p.ruolo, 0) < max_per_role and not player_taken_in_league(team.league_id, p.id)
    ]
    if not candidates:
        raise BusinessRuleError("Non ci sono player disponibili per completare la rosa")
    cheapest = candidates[0]
    if team.crediti_residui >= cheapest.quotazione:
        raise BusinessRuleError(
            "Hai ancora abbastanza crediti per acquistare il player disponibile meno costoso")

    locked = ProPlayer.objects.select_for_update().filter(pk=cheapest.pk).first()
    if locked is None:
        raise ResourceNotFound(f"Player non trovato con id: {cheapest.pk}")
    if player_taken_in_league(team.league_id, locked.id):
        raise BusinessRuleError("Il player è appena stato acquistato da un'altra squadra: riprova")
    return RosterEntry.objects.create(fanta_team=team, player=locked, crediti_spesi=0)


@transaction.atomic
def completa_rosa_casualmente(user, team_id) -> FantaTeam:
    team = get_fanta_team_or_404(team_id)
    assert_team_owner(user, team)
    max_size, max_per_role = team.league.roster_limits
    if team.rosa.count() >= max_size:
        raise BusinessRuleError("La rosa è già completa")

    counts = roster_counts_by_role(team)
    available = [
        p for p in ProPlayer.objects.filter(competition=team.league.competition)
        if counts.get(p.ruolo, 0) < max_per_role and not player_taken_in_league(team.league_id, p.id)
    ]
    if not available:
        raise BusinessRuleError("Non ci sono abbastanza player disponibili")
    cheapest = min(p.quotazione for p in available)
    if team.crediti_residui >= cheapest:
        raise BusinessRuleError("Puoi ancora permetterti un player disponibile: continua con l'asta")

    selected: list[ProPlayer] = []
    for role in ROLE_ORDER:
        missing = max_per_role - counts.get(role.value, 0)
        pool = [p for p in available if p.ruolo == role.value]
        random.shuffle(pool)
        if len(pool) < missing:
            raise BusinessRuleError(f"Non ci sono abbastanza player disponibili nel ruolo {role.value}")
        selected.extend(pool[:missing])

    for candidate in selected:
        locked = ProPlayer.objects.select_for_update().filter(pk=candidate.pk).first()
        if locked is None:
            raise ResourceNotFound("Player non trovato")
        if player_taken_in_league(team.league_id, locked.id):
            raise BusinessRuleError("Un player casuale è appena stato assegnato: riprova")
        RosterEntry.objects.create(fanta_team=team, player=locked, crediti_spesi=0)
    return team


@transaction.atomic
def rilascia_player(user, team_id, roster_entry_id) -> None:
    team = get_fanta_team_or_404(team_id)
    assert_team_owner(user, team)
    entry = RosterEntry.objects.filter(pk=roster_entry_id).first()
    if entry is None:
        raise ResourceNotFound(f"Voce di rosa non trovata con id: {roster_entry_id}")
    if entry.fanta_team_id != team.id:
        raise BusinessRuleError("La voce di rosa indicata non appartiene a questa squadra")
    # Rimborso parziale (50%) come nella versione Java.
    team.crediti_residui += entry.crediti_spesi // 2
    team.save(update_fields=["crediti_residui"])
    entry.delete()


# --------------------------------------------------------------------------
# Asta a crediti
# --------------------------------------------------------------------------
def assert_auction_open(league: League) -> None:
    if not league.auction_open:
        raise BusinessRuleError("L'asta della lega non è aperta")


def assert_participant_or_admin(user, league: League) -> None:
    if user.is_global_admin:
        return
    if not FantaTeam.objects.filter(league=league, owner=user).exists():
        raise BusinessRuleError("Non partecipi a questa lega")


def assert_bidder_or_admin(user, team: FantaTeam) -> None:
    if team.owner_id != user.id and not user.is_global_admin:
        raise BusinessRuleError("Non puoi offrire per questa squadra")


@transaction.atomic
def start_auction(user, league_id, player_id, fanta_team_id) -> AuctionSession:
    league = get_league_for_update(league_id)
    assert_auction_open(league)
    assert_participant_or_admin(user, league)
    if AuctionSession.objects.filter(league=league, status=AuctionStatus.ACTIVE).exists():
        raise BusinessRuleError("C'è già un'asta attiva in questa lega")

    player = ProPlayer.objects.select_for_update().filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFound("Player non trovato")
    if player_taken_in_league(league.id, player.id):
        raise BusinessRuleError("Questo player è già assegnato nella lega")

    opening_bidder = FantaTeam.objects.select_related("league", "owner").filter(pk=fanta_team_id).first()
    if opening_bidder is None:
        raise ResourceNotFound("FantaTeam non trovata")
    if opening_bidder.league_id != league.id:
        raise BusinessRuleError("La squadra non partecipa a questa lega")
    assert_bidder_or_admin(user, opening_bidder)
    validate_roster_slot(opening_bidder, player)
    if opening_bidder.crediti_residui < player.quotazione:
        raise BusinessRuleError("Crediti insufficienti per avviare l'asta")

    return AuctionSession.objects.create(
        league=league,
        player=player,
        highest_bidder=opening_bidder,
        current_bid=player.quotazione,
        ends_at=timezone.now() + timedelta(seconds=SECONDS_PER_BID),
        status=AuctionStatus.ACTIVE,
    )


@transaction.atomic
def place_bid(user, auction_id, fanta_team_id, credits: int) -> AuctionSession:
    auction = (AuctionSession.objects.select_for_update()
               .select_related("league", "player", "highest_bidder").filter(pk=auction_id).first())
    if auction is None:
        raise ResourceNotFound("Asta non trovata")
    assert_auction_open(auction.league)
    if auction.status != AuctionStatus.ACTIVE or auction.ends_at <= timezone.now():
        finalize_auction(auction)
        raise BusinessRuleError("L'asta è terminata")

    team = FantaTeam.objects.select_related("league", "owner").filter(pk=fanta_team_id).first()
    if team is None:
        raise ResourceNotFound("FantaTeam non trovata")
    if team.league_id != auction.league_id:
        raise BusinessRuleError("La squadra non partecipa a questa lega")
    assert_bidder_or_admin(user, team)
    if auction.highest_bidder_id == team.id:
        raise BusinessRuleError("Sei già il miglior offerente")

    minimum = auction.current_bid if auction.highest_bidder_id is None else auction.current_bid + 1
    if credits < minimum:
        raise BusinessRuleError(f"L'offerta minima è {minimum} crediti")
    if credits > team.crediti_residui:
        raise BusinessRuleError("Crediti insufficienti")
    validate_roster_slot(team, auction.player)

    auction.highest_bidder = team
    auction.current_bid = credits
    # Ogni rilancio riarma il countdown.
    auction.ends_at = timezone.now() + timedelta(seconds=SECONDS_PER_BID)
    auction.save(update_fields=["highest_bidder", "current_bid", "ends_at"])
    return auction


def active_auction(league_id) -> AuctionSession | None:
    return (AuctionSession.objects.select_related("league", "player", "highest_bidder")
            .filter(league_id=league_id, status=AuctionStatus.ACTIVE).order_by("id").first())


def finalize_auction(auction: AuctionSession) -> None:
    """Assegna il player al miglior offerente, o fa scadere l'asta."""
    if auction.status != AuctionStatus.ACTIVE:
        return
    winner = auction.highest_bidder
    if winner is None:
        auction.status = AuctionStatus.EXPIRED
    elif (winner.crediti_residui >= auction.current_bid
            and not player_taken_in_league(auction.league_id, auction.player_id)):
        try:
            validate_roster_slot(winner, auction.player)
        except BusinessRuleError:
            auction.status = AuctionStatus.EXPIRED
            auction.save(update_fields=["status"])
            return
        winner.crediti_residui -= auction.current_bid
        winner.save(update_fields=["crediti_residui"])
        RosterEntry.objects.create(fanta_team=winner, player=auction.player,
                                   crediti_spesi=auction.current_bid)
        auction.status = AuctionStatus.WON
    else:
        auction.status = AuctionStatus.EXPIRED
    auction.save(update_fields=["status"])


@transaction.atomic
def finalize_expired_auctions() -> int:
    """Equivalente dello `@Scheduled(fixedDelay = 500)` Java."""
    expired = AuctionSession.objects.filter(status=AuctionStatus.ACTIVE, ends_at__lte=timezone.now())
    count = 0
    for auction in expired:
        locked = (AuctionSession.objects.select_for_update()
                  .select_related("league", "player", "highest_bidder").filter(pk=auction.pk).first())
        if locked is not None:
            finalize_auction(locked)
            count += 1
    return count
