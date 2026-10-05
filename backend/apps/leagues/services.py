"""Leghe, FantaTeam e rose (porting di ``LeagueService`` e ``FantaTeamService``)."""

from __future__ import annotations

import random
from collections import Counter, defaultdict

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.common.exceptions import AccessDeniedException, BusinessRuleException, ResourceNotFoundException
from apps.common.utils import ROLE_VALUES
from apps.competitions.models import CompetitionEdition, Ruleset
from apps.esports.models import EditionRoster, ProPlayer
from apps.users.models import Role, User

from . import policy
from .models import AuctionSession, AuctionStatus, FantaTeam, League, RosterEntry

WORLDS_DEFAULT_SETTINGS = {
    "budget": 100,
    "max_participants": policy.WORLDS_MAX_PARTICIPANTS,
    "free_transfers_per_matchday": 2,
    "extra_transfer_penalty": 3,
    "captain_multiplier": 2,
    "lock_minutes": 60,
    "worlds_exclusive": False,
    "auto_close_matchdays": True,
}
REGIONAL_DEFAULT_SETTINGS = {"auto_close_matchdays": True}


# --------------------------------------------------------------------------- risposte
def league_response(league: League) -> dict:
    numero_squadre = league.fanta_teams.count()
    limits = policy.roster_limits(league)
    edition = league.edition
    return {
        "id": league.id,
        "nome": league.nome,
        "codice_invito": league.codice_invito,
        "crediti_iniziali": league.crediti_iniziali,
        "admin_username": league.admin.username,
        "numero_squadre": numero_squadre,
        "auction_open": league.auction_open,
        "participant_count": league.participant_count,
        "competition_started": league.competition_started,
        "max_roster_size": limits.max_roster_size,
        "max_per_role": limits.max_per_role,
        "max_participants": policy.max_participants(league),
        "competition": edition.competition.code,
        "edition_id": edition.id,
        "edition_name": edition.name,
        "ruleset": league.ruleset,
        "settings": league.settings,
    }


def roster_entry_response(entry: RosterEntry, roster: dict[int, EditionRoster] | None = None) -> dict:
    info = (roster or {}).get(entry.player_id)
    if info is None:
        info = active_roster_entry(entry.league.edition_id, entry.player_id)
    return {
        "id": entry.id,
        "lec_player_id": entry.player_id,
        "lec_player_nickname": entry.player.nickname,
        "ruolo": info.role if info else None,
        "crediti_spesi": entry.crediti_spesi,
        "data_acquisto": entry.data_acquisto,
        "team_id": info.team_id if info else None,
        "team_nome": info.team.name if info else None,
        "quotazione": info.quotazione if info else None,
    }


def fanta_team_response(team: FantaTeam, punti: float | None = None) -> dict:
    entries = list(team.rosa.select_related("player", "league").all())
    roster = edition_roster_map(team.league.edition_id, [e.player_id for e in entries])
    credits = team.crediti_residui
    if team.league.is_worlds:
        from apps.worlds.services import available_credits

        credits = available_credits(team)
    return {
        "id": team.id,
        "nome": team.nome,
        "crediti_residui": credits,
        "league_id": team.league_id,
        "league_nome": team.league.nome,
        "owner_username": team.owner.username,
        "punti": punti,
        "rosa": [roster_entry_response(e, roster) for e in entries],
    }


# --------------------------------------------------------------------------- query di supporto
def active_roster_entry(edition_id: int, player_id: int) -> EditionRoster | None:
    return edition_roster_map(edition_id, [player_id]).get(player_id)


def edition_roster_map(edition_id: int, player_ids) -> dict[int, EditionRoster]:
    result: dict[int, EditionRoster] = {}
    for entry in (
        EditionRoster.objects.select_related("team")
        .filter(edition_id=edition_id, player_id__in=list(player_ids))
        .order_by("active_from")
    ):
        if entry.player_id not in result or entry.active_to is None:
            result[entry.player_id] = entry
    return result


def available_players(edition_id: int) -> list[EditionRoster]:
    return list(
        EditionRoster.objects.select_related("player", "team")
        .filter(edition_id=edition_id, active_to__isnull=True)
        .order_by("quotazione", "player__nickname")
    )


def is_global_admin(user: User) -> bool:
    return user.role == Role.ADMIN


def get_league(league_id: int) -> League:
    try:
        return League.objects.select_related("edition__competition", "admin").get(pk=league_id)
    except League.DoesNotExist:
        raise ResourceNotFoundException(f"Lega non trovata con id: {league_id}")


def get_league_for_update(league_id: int) -> League:
    try:
        return (
            League.objects.select_for_update()
            .select_related("edition__competition", "admin")
            .get(pk=league_id)
        )
    except League.DoesNotExist:
        raise ResourceNotFoundException(f"Lega non trovata con id: {league_id}")


def get_team(team_id: int) -> FantaTeam:
    try:
        return FantaTeam.objects.select_related("league__edition__competition", "owner").get(pk=team_id)
    except FantaTeam.DoesNotExist:
        raise ResourceNotFoundException(f"FantaTeam non trovata con id: {team_id}")


def assert_can_view(user: User, league: League) -> None:
    if is_global_admin(user) or league.admin_id == user.id:
        return
    if not league.fanta_teams.filter(owner=user).exists():
        raise AccessDeniedException("You cannot access this league")


def assert_creator_or_admin(user: User, league: League, message: str) -> None:
    if not is_global_admin(user) and league.admin_id != user.id:
        raise BusinessRuleException(message)


def assert_owner(team: FantaTeam, user: User) -> None:
    if team.owner_id != user.id and not is_global_admin(user):
        raise BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica")


# --------------------------------------------------------------------------- leghe
def accessible_leagues(user: User):
    qs = League.objects.select_related("edition__competition", "admin")
    if is_global_admin(user):
        return qs.order_by("id")
    return qs.filter(Q(admin=user) | Q(fanta_teams__owner=user)).distinct().order_by("id")


@transaction.atomic
def create_league(
    user: User,
    *,
    nome: str,
    edition_id: int | None,
    competition: str | None,
    crediti_iniziali: int | None,
    league_settings: dict | None = None,
) -> League:
    edition = _resolve_edition(edition_id, competition)
    ruleset = edition.competition.ruleset
    if ruleset == Ruleset.WORLDS:
        merged = {**WORLDS_DEFAULT_SETTINGS, **(league_settings or {})}
        if merged.get("worlds_exclusive"):
            raise BusinessRuleException("La variante WORLDS con esclusività non è ancora disponibile")
        credits = int(merged["budget"])
    else:
        merged = {**REGIONAL_DEFAULT_SETTINGS, **(league_settings or {})}
        credits = crediti_iniziali if crediti_iniziali is not None else settings.CREDITI_INIZIALI_DEFAULT
    return League.objects.create(
        nome=nome, crediti_iniziali=credits, admin=user, edition=edition, ruleset=ruleset, settings=merged
    )


def _resolve_edition(edition_id: int | None, competition: str | None) -> CompetitionEdition:
    from apps.common.utils import now

    qs = CompetitionEdition.objects.select_related("competition")
    if edition_id is not None:
        edition = qs.filter(pk=edition_id).first()
        if edition is None:
            raise ResourceNotFoundException(f"Edizione non trovata con id: {edition_id}")
    elif competition:
        edition = (
            qs.filter(competition__code__iexact=competition, is_active=True).order_by("-starts_at").first()
        )
        if edition is None:
            raise BusinessRuleException(f"Nessuna edizione attiva per la competizione {competition.upper()}")
    else:
        raise BusinessRuleException("Scegli la competizione e l'edizione della lega")
    if not edition.is_active and (edition.ends_at is not None and edition.ends_at < now()):
        raise BusinessRuleException("Puoi creare leghe solo su edizioni attive o future")
    return edition


@transaction.atomic
def delete_league(user: User, league_id: int) -> None:
    league = get_league(league_id)
    if not is_global_admin(user) and league.admin_id != user.id:
        raise AccessDeniedException("You cannot delete this league")
    league.delete()


@transaction.atomic
def open_auction(user: User, league_id: int) -> League:
    league = get_league_for_update(league_id)
    assert_creator_or_admin(user, league, "Solo il creatore della lega può gestire l'asta")
    if league.is_worlds:
        raise BusinessRuleException("Le leghe WORLDS non prevedono l'asta: si compra dal listone")
    if not league.competition_started:
        raise BusinessRuleException("Crea una giornata prima di aprire l'asta")
    league.auction_open = True
    league.save(update_fields=["auction_open"])
    return league


@transaction.atomic
def close_auction(user: User, league_id: int) -> League:
    league = get_league_for_update(league_id)
    assert_creator_or_admin(user, league, "Solo il creatore della lega può gestire l'asta")
    if AuctionSession.objects.filter(league=league, status=AuctionStatus.ACTIVE).exists():
        raise BusinessRuleException(
            "Attendi la fine dell'asta del player prima di terminare l'asta della lega"
        )
    league.auction_open = False
    league.save(update_fields=["auction_open"])
    from apps.lineups.services import ensure_fixed_roster_periods

    for team in league.fanta_teams.all():
        ensure_fixed_roster_periods(team)
    return league


def start_competition(league: League) -> League:
    league.freeze_participant_count(league.fanta_teams.count())
    if not league.is_worlds:
        league.auction_open = True
    league.save(update_fields=["participant_count", "auction_open"])
    return league


def _roles_count(entries: list[RosterEntry], roster: dict[int, EditionRoster]) -> Counter:
    return Counter(roster[e.player_id].role for e in entries if e.player_id in roster)


@transaction.atomic
def complete_all_rosters_randomly(user: User, league_id: int) -> list[FantaTeam]:
    league = get_league_for_update(league_id)
    assert_creator_or_admin(user, league, "Solo il creatore della lega può gestire l'asta")
    if league.is_worlds:
        raise BusinessRuleException("Nelle leghe WORLDS ogni partecipante compone la rosa dal listone")
    if league.auction_open:
        raise BusinessRuleException("Termina l'asta della lega prima di completare casualmente le rose")
    limits = policy.roster_limits(league)
    teams = list(league.fanta_teams.order_by("id"))
    taken = set(RosterEntry.objects.filter(league=league).values_list("player_id", flat=True))
    pool: dict[str, list[EditionRoster]] = defaultdict(list)
    for entry in available_players(league.edition_id):
        if entry.player_id not in taken:
            pool[entry.role].append(entry)
    for role_pool in pool.values():
        random.shuffle(role_pool)
    assignments: list[tuple[FantaTeam, list[EditionRoster]]] = []
    for team in teams:
        current = list(team.rosa.all())
        if len(current) >= limits.max_roster_size:
            continue
        roster = edition_roster_map(league.edition_id, [e.player_id for e in current])
        counts = _roles_count(current, roster)
        selected = []
        for role in ROLE_VALUES:
            missing = (limits.max_per_role or 0) - counts.get(role, 0)
            if len(pool[role]) < missing:
                raise BusinessRuleException(
                    "Non ci sono abbastanza player disponibili per completare tutte le rose"
                )
            for _ in range(max(0, missing)):
                selected.append(pool[role].pop())
        assignments.append((team, selected))
    assigned: set[int] = set()
    for team, selected in assignments:
        for entry in selected:
            if entry.player_id in assigned:
                raise BusinessRuleException("Un player casuale è stato selezionato più volte")
            assigned.add(entry.player_id)
            RosterEntry.objects.create(fanta_team=team, league=league, player=entry.player, crediti_spesi=0)
    from apps.lineups.services import ensure_fixed_roster_periods

    for team in teams:
        ensure_fixed_roster_periods(team)
    return teams


# --------------------------------------------------------------------------- FantaTeam
@transaction.atomic
def join_league(user: User, codice_invito: str, nome_squadra: str) -> FantaTeam:
    league = League.objects.select_for_update().filter(codice_invito=codice_invito).first()
    if league is None:
        raise BusinessRuleException(f"Nessuna lega trovata con codice invito: {codice_invito}")
    if league.competition_started and not league.is_worlds:
        raise BusinessRuleException("La lega è già iniziata: non è più possibile iscriversi")
    limit = policy.max_participants(league)
    if league.fanta_teams.count() >= limit:
        raise BusinessRuleException(f"La lega ha già raggiunto il limite di {limit} squadre")
    if league.fanta_teams.filter(owner=user).exists():
        raise BusinessRuleException("Sei già iscritto a questa lega con una squadra")
    return FantaTeam.objects.create(
        nome=nome_squadra, crediti_residui=league.crediti_iniziali, league=league, owner=user
    )


def teams_by_league(user: User, league_id: int) -> list[FantaTeam]:
    league = get_league(league_id)
    assert_can_view(user, league)
    return list(league.fanta_teams.select_related("league__edition", "owner").order_by("id"))


def my_teams(user: User) -> list[FantaTeam]:
    return list(
        FantaTeam.objects.filter(owner=user).select_related("league__edition", "owner").order_by("id")
    )


def team_for_viewer(user: User, team_id: int) -> FantaTeam:
    team = get_team(team_id)
    assert_can_view(user, team.league)
    return team


def _lock_player(player_id: int) -> ProPlayer:
    try:
        return ProPlayer.objects.select_for_update().get(pk=player_id)
    except ProPlayer.DoesNotExist:
        raise ResourceNotFoundException(f"Player non trovato con id: {player_id}")


@transaction.atomic
def buy_player(user: User, team_id: int, player_id: int, credits: int) -> RosterEntry:
    """Acquisto diretto a crediti (porting di ``acquistaPlayer``), usato fuori dall'asta live."""
    team = FantaTeam.objects.select_for_update().select_related("league__edition", "owner").filter(
        pk=team_id).first()
    if team is None:
        raise ResourceNotFoundException(f"FantaTeam non trovata con id: {team_id}")
    assert_owner(team, user)
    league = team.league
    player = _lock_player(player_id)
    info = active_roster_entry(league.edition_id, player.id)
    if info is None:
        raise ResourceNotFoundException(f"Player non trovato con id: {player_id}")
    if RosterEntry.objects.filter(league=league, player=player).exists() and not league.is_worlds:
        raise BusinessRuleException(f"Il player {player.nickname} è già stato acquistato in questa lega")
    if credits > team.crediti_residui:
        raise BusinessRuleException(f"Crediti insufficienti: residui {team.crediti_residui}, offerti {credits}")
    if credits < info.quotazione:
        raise BusinessRuleException(
            f"L'offerta ({credits}) è inferiore alla quotazione base del player ({info.quotazione})")
    limits = policy.roster_limits(league)
    rosa = list(team.rosa.all())
    if len(rosa) >= limits.max_roster_size:
        raise BusinessRuleException(f"Rosa al completo: massimo {limits.max_roster_size} player")
    roster = edition_roster_map(league.edition_id, [e.player_id for e in rosa])
    if limits.max_per_role is not None and _roles_count(rosa, roster).get(info.role, 0) >= limits.max_per_role:
        raise BusinessRuleException(f"Hai già raggiunto il numero massimo di player per il ruolo {info.role}")
    team.crediti_residui -= credits
    team.save(update_fields=["crediti_residui"])
    return add_roster_entry(team, player, credits)


@transaction.atomic
def free_player(user: User, team_id: int) -> RosterEntry:
    """Assegna gratis il player disponibile meno costoso (porting di ``acquistaPlayerGratis``)."""
    team = get_team(team_id)
    assert_owner(team, user)
    league = team.league
    if league.is_worlds:
        raise BusinessRuleException("Funzione non disponibile nelle leghe WORLDS")
    limits = policy.roster_limits(league)
    rosa = list(team.rosa.all())
    if len(rosa) >= limits.max_roster_size:
        raise BusinessRuleException("La rosa è già completa")
    others_complete = all(
        other.rosa.count() >= limits.max_roster_size for other in league.fanta_teams.exclude(pk=team.pk)
    )
    if not others_complete:
        raise BusinessRuleException(
            "Il player gratis è disponibile solo quando tutte le altre squadre hanno completato la rosa"
        )
    roster = edition_roster_map(league.edition_id, [e.player_id for e in rosa])
    counts = _roles_count(rosa, roster)
    taken = set(RosterEntry.objects.filter(league=league).values_list("player_id", flat=True))
    candidates = [
        e
        for e in available_players(league.edition_id)
        if counts.get(e.role, 0) < (limits.max_per_role or 0) and e.player_id not in taken
    ]
    if not candidates:
        raise BusinessRuleException("Non ci sono player disponibili per completare la rosa")
    cheapest = min(candidates, key=lambda e: e.quotazione)
    if team.crediti_residui >= cheapest.quotazione:
        raise BusinessRuleException(
            "Hai ancora abbastanza crediti per acquistare il player disponibile meno costoso"
        )
    player = _lock_player(cheapest.player_id)
    if RosterEntry.objects.filter(league=league, player=player).exists():
        raise BusinessRuleException("Il player è appena stato acquistato da un'altra squadra: riprova")
    entry = RosterEntry.objects.create(fanta_team=team, league=league, player=player, crediti_spesi=0)
    from apps.lineups.services import ensure_fixed_roster_periods

    ensure_fixed_roster_periods(team)
    return entry


@transaction.atomic
def release_player(user: User, team_id: int, roster_entry_id: int) -> None:
    team = get_team(team_id)
    assert_owner(team, user)
    if team.league.is_worlds:
        raise BusinessRuleException("Nelle leghe WORLDS usa i cambi di mercato per vendere un player")
    entry = RosterEntry.objects.filter(pk=roster_entry_id).first()
    if entry is None:
        raise ResourceNotFoundException(f"Voce di rosa non trovata con id: {roster_entry_id}")
    if entry.fanta_team_id != team.id:
        raise BusinessRuleException("La voce di rosa indicata non appartiene a questa squadra")
    # Rimborso parziale (50%) dei crediti spesi, per disincentivare acquisti/rilasci speculativi.
    team.crediti_residui += entry.crediti_spesi // 2
    team.save(update_fields=["crediti_residui"])
    entry.delete()


def add_roster_entry(team: FantaTeam, player: ProPlayer, credits: int) -> RosterEntry:
    try:
        with transaction.atomic():
            return RosterEntry.objects.create(
                fanta_team=team, league=team.league, player=player, crediti_spesi=credits
            )
    except IntegrityError:
        raise BusinessRuleException(f"Il player {player.nickname} è già stato acquistato in questa lega")
