"""Regole della modalità Worlds.

Riusa la formula fantapunti per-ruolo di `scoring/`, ma con:
 - rosa e budget configurabili per edizione (default 10 player, 2 per ruolo);
 - formazione di 5 titolari (uno per ruolo) da confermare entro la deadline
   della fase, invece della finestra settimanale martedì-giovedì;
 - sostituzione libera fra una fase e l'altra (`allow_reentry_swap`);
 - punteggio **cumulativo per fase** (somma, non media) più i bonus torneo.
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.exceptions import AccessDenied, BusinessRuleError, ResourceNotFound
from ingest.models import GamePlayerStat, Match
from teams.models import ROLE_ORDER, ProPlayer

from . import bonuses
from .models import (
    WorldsAuctionSession,
    WorldsAuctionStatus,
    WorldsEdition,
    WorldsLeague,
    WorldsRosterEntry,
    WorldsStage,
    WorldsStageLineup,
    WorldsTeam,
)

SECONDS_PER_BID = settings.FANTALOL["AUCTION_SECONDS_PER_BID"]
NUMERO_TITOLARI = len(ROLE_ORDER)


# --------------------------------------------------------------------------
# Lookup e autorizzazioni
# --------------------------------------------------------------------------
def get_edition_or_404(edition_id) -> WorldsEdition:
    edition = WorldsEdition.objects.filter(pk=edition_id).first()
    if edition is None:
        raise ResourceNotFound(f"Edizione Worlds non trovata con id: {edition_id}")
    return edition


def get_stage_or_404(stage_id) -> WorldsStage:
    stage = WorldsStage.objects.select_related("edition").filter(pk=stage_id).first()
    if stage is None:
        raise ResourceNotFound(f"Fase Worlds non trovata con id: {stage_id}")
    return stage


def get_league_or_404(league_id) -> WorldsLeague:
    league = WorldsLeague.objects.select_related("edition", "admin").filter(pk=league_id).first()
    if league is None:
        raise ResourceNotFound(f"Lega Worlds non trovata con id: {league_id}")
    return league


def get_team_or_404(team_id) -> WorldsTeam:
    team = WorldsTeam.objects.select_related("league", "league__edition", "owner").filter(pk=team_id).first()
    if team is None:
        raise ResourceNotFound(f"Squadra Worlds non trovata con id: {team_id}")
    return team


def assert_can_view(user, league: WorldsLeague) -> None:
    if user.is_global_admin or league.admin_id == user.id:
        return
    if WorldsTeam.objects.filter(league=league, owner=user).exists():
        return
    raise AccessDenied("Non hai accesso a questa lega Worlds")


def assert_league_admin(user, league: WorldsLeague) -> None:
    if not user.is_global_admin and league.admin_id != user.id:
        raise BusinessRuleError("Solo il creatore della lega può gestire l'asta")


def assert_team_owner(user, team: WorldsTeam) -> None:
    if team.owner_id != user.id and not user.is_global_admin:
        raise BusinessRuleError("Non sei il proprietario di questa squadra")


def visible_leagues(user):
    if user.is_global_admin:
        return WorldsLeague.objects.all().order_by("id")
    return (WorldsLeague.objects
            .filter(Q(admin=user) | Q(teams__owner=user))
            .distinct()
            .order_by("id"))


# --------------------------------------------------------------------------
# Edizioni, fasi e player pool
# --------------------------------------------------------------------------
@transaction.atomic
def mark_worlds_pool(edition: WorldsEdition) -> int:
    """Marca `is_worlds_eligible` sui roster delle squadre qualificate.

    Il pool Worlds non è vincolato a un solo competitivo: contiene i player di
    ogni regione qualificata.
    """
    team_ids = list(edition.qualified_teams.values_list("id", flat=True))
    if not team_ids:
        return 0
    return ProPlayer.objects.filter(team_id__in=team_ids).update(is_worlds_eligible=True)


def worlds_player_pool(edition: WorldsEdition):
    """Player selezionabili all'asta di una lega Worlds."""
    team_ids = list(edition.qualified_teams.values_list("id", flat=True))
    queryset = ProPlayer.objects.select_related("team")
    if team_ids:
        return queryset.filter(team_id__in=team_ids)
    return queryset.filter(is_worlds_eligible=True)


@transaction.atomic
def import_stage_matches(stage: WorldsStage, client=None) -> int:
    """Importa da PandaScore le serie della fase e le aggancia allo stage."""
    from ingest.pandascore_client import PandaScoreClient
    from ingest.services import upsert_match

    tournament_id = stage.pandascore_tournament_id or stage.edition.pandascore_tournament_id
    if not tournament_id:
        raise BusinessRuleError("La fase non ha un tournament id PandaScore configurato")
    client = client or PandaScoreClient()
    if not client.configured:
        raise BusinessRuleError("PANDASCORE_API_TOKEN assente: impossibile importare le serie")

    imported = 0
    for payload in client.tournament_matches(tournament_id):
        match, _ = upsert_match(payload, "WORLDS")
        match.worlds_stage = stage
        match.save(update_fields=["worlds_stage"])
        imported += 1

    if imported and stage.lineup_deadline is None:
        first = Match.objects.filter(worlds_stage=stage).order_by("begin_at").first()
        if first and first.begin_at:
            stage.lineup_deadline = first.begin_at
            stage.save(update_fields=["lineup_deadline"])
    return imported


def current_stage(edition: WorldsEdition, *, now=None) -> WorldsStage | None:
    """La prima fase la cui deadline non è ancora passata."""
    now = now or timezone.now()
    for stage in edition.stages.all().order_by("ordine"):
        deadline = stage.effective_deadline()
        if deadline is None or deadline > now:
            return stage
    return edition.stages.order_by("-ordine").first()


def lock_due_stage_lineups(*, now=None) -> int:
    """Chiude le formazioni delle fasi la cui deadline è scaduta."""
    now = now or timezone.now()
    locked = 0
    for stage in WorldsStage.objects.filter(lineups_locked=False).select_related("edition"):
        deadline = stage.effective_deadline()
        if deadline is not None and deadline <= now:
            stage.lineups_locked = True
            stage.save(update_fields=["lineups_locked"])
            locked += 1
    return locked


# --------------------------------------------------------------------------
# Leghe Worlds
# --------------------------------------------------------------------------
@transaction.atomic
def create_league(user, edition_id, nome: str, **overrides) -> WorldsLeague:
    edition = get_edition_or_404(edition_id)
    return WorldsLeague.objects.create(
        nome=nome,
        edition=edition,
        admin=user,
        crediti_iniziali=overrides.get("crediti_iniziali") or edition.default_crediti,
        roster_size=overrides.get("roster_size") or edition.default_roster_size,
        max_per_role=overrides.get("max_per_role") or edition.default_max_per_role,
        allow_reentry_swap=overrides.get("allow_reentry_swap", True),
        mvp_bonus=overrides.get("mvp_bonus", 3.0),
        series_win_bonus=overrides.get("series_win_bonus", 1.0),
    )


@transaction.atomic
def join_league(user, codice_invito: str, nome_squadra: str) -> WorldsTeam:
    league = WorldsLeague.objects.filter(codice_invito=codice_invito).first()
    if league is None:
        raise BusinessRuleError(f"Nessuna lega Worlds trovata con codice invito: {codice_invito}")
    if WorldsTeam.objects.filter(league=league, owner=user).exists():
        raise BusinessRuleError("Sei già iscritto a questa lega con una squadra")
    if league.auction_open:
        raise BusinessRuleError("L'asta è già iniziata: non è più possibile iscriversi")
    return WorldsTeam.objects.create(
        nome=nome_squadra, league=league, owner=user, crediti_residui=league.crediti_iniziali)


@transaction.atomic
def set_auction_open(user, league_id, open_: bool) -> WorldsLeague:
    league = get_league_or_404(league_id)
    assert_league_admin(user, league)
    if not open_ and WorldsAuctionSession.objects.filter(
            league=league, status=WorldsAuctionStatus.ACTIVE).exists():
        raise BusinessRuleError("Attendi la fine dell'asta del player prima di chiuderla")
    league.auction_open = open_
    league.save(update_fields=["auction_open"])
    return league


# --------------------------------------------------------------------------
# Rosa e asta
# --------------------------------------------------------------------------
def roster_counts_by_role(team: WorldsTeam) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in active_roster(team):
        counts[entry.player.ruolo] = counts.get(entry.player.ruolo, 0) + 1
    return counts


def active_roster(team: WorldsTeam):
    """Rosa corrente: esclude i player rilasciati con una sostituzione."""
    return list(team.rosa.select_related("player", "player__team")
                .filter(released_at_stage__isnull=True))


def player_taken_in_league(league_id, player_id) -> bool:
    return WorldsRosterEntry.objects.filter(
        fanta_team__league_id=league_id, player_id=player_id, released_at_stage__isnull=True).exists()


def validate_roster_slot(team: WorldsTeam, player: ProPlayer) -> None:
    league = team.league
    if len(active_roster(team)) >= league.roster_size:
        raise BusinessRuleError("Rosa già completa")
    if roster_counts_by_role(team).get(player.ruolo, 0) >= league.max_per_role:
        raise BusinessRuleError(f"Hai già raggiunto il limite per il ruolo {player.ruolo}")


def assert_eligible(league: WorldsLeague, player: ProPlayer) -> None:
    if not worlds_player_pool(league.edition).filter(pk=player.pk).exists():
        raise BusinessRuleError(
            f"{player.nickname} non fa parte del player pool di {league.edition.nome}")


@transaction.atomic
def start_auction(user, league_id, player_id, team_id) -> WorldsAuctionSession:
    league = get_league_or_404(league_id)
    if not league.auction_open:
        raise BusinessRuleError("L'asta della lega non è aperta")
    assert_can_view(user, league)
    if WorldsAuctionSession.objects.filter(league=league, status=WorldsAuctionStatus.ACTIVE).exists():
        raise BusinessRuleError("C'è già un'asta attiva in questa lega")

    player = ProPlayer.objects.select_for_update().filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFound("Player non trovato")
    assert_eligible(league, player)
    if player_taken_in_league(league.id, player.id):
        raise BusinessRuleError("Questo player è già assegnato nella lega")

    team = get_team_or_404(team_id)
    if team.league_id != league.id:
        raise BusinessRuleError("La squadra non partecipa a questa lega")
    assert_team_owner(user, team)
    validate_roster_slot(team, player)
    if team.crediti_residui < player.quotazione:
        raise BusinessRuleError("Crediti insufficienti per avviare l'asta")

    return WorldsAuctionSession.objects.create(
        league=league, player=player, highest_bidder=team, current_bid=player.quotazione,
        ends_at=timezone.now() + timedelta(seconds=SECONDS_PER_BID),
        status=WorldsAuctionStatus.ACTIVE)


@transaction.atomic
def place_bid(user, auction_id, team_id, credits: int) -> WorldsAuctionSession:
    auction = (WorldsAuctionSession.objects.select_for_update()
               .select_related("league", "player", "highest_bidder").filter(pk=auction_id).first())
    if auction is None:
        raise ResourceNotFound("Asta non trovata")
    if auction.status != WorldsAuctionStatus.ACTIVE or auction.ends_at <= timezone.now():
        finalize_auction(auction)
        raise BusinessRuleError("L'asta è terminata")

    team = get_team_or_404(team_id)
    if team.league_id != auction.league_id:
        raise BusinessRuleError("La squadra non partecipa a questa lega")
    assert_team_owner(user, team)
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
    auction.ends_at = timezone.now() + timedelta(seconds=SECONDS_PER_BID)
    auction.save(update_fields=["highest_bidder", "current_bid", "ends_at"])
    return auction


def finalize_auction(auction: WorldsAuctionSession) -> None:
    if auction.status != WorldsAuctionStatus.ACTIVE:
        return
    winner = auction.highest_bidder
    if winner is None or winner.crediti_residui < auction.current_bid \
            or player_taken_in_league(auction.league_id, auction.player_id):
        auction.status = WorldsAuctionStatus.EXPIRED
    else:
        try:
            validate_roster_slot(winner, auction.player)
        except BusinessRuleError:
            auction.status = WorldsAuctionStatus.EXPIRED
            auction.save(update_fields=["status"])
            return
        winner.crediti_residui -= auction.current_bid
        winner.save(update_fields=["crediti_residui"])
        WorldsRosterEntry.objects.update_or_create(
            fanta_team=winner, player=auction.player,
            defaults={"crediti_spesi": auction.current_bid, "released_at_stage": None})
        auction.status = WorldsAuctionStatus.WON
    auction.save(update_fields=["status"])


@transaction.atomic
def finalize_expired_auctions() -> int:
    count = 0
    for auction in WorldsAuctionSession.objects.filter(
            status=WorldsAuctionStatus.ACTIVE, ends_at__lte=timezone.now()):
        locked = (WorldsAuctionSession.objects.select_for_update()
                  .select_related("league", "player", "highest_bidder").filter(pk=auction.pk).first())
        if locked is not None:
            finalize_auction(locked)
            count += 1
    return count


@transaction.atomic
def complete_roster_randomly(user, team_id) -> WorldsTeam:
    """Completa gratuitamente la rosa con player liberi del pool Worlds."""
    team = get_team_or_404(team_id)
    assert_team_owner(user, team)
    league = team.league
    counts = roster_counts_by_role(team)
    missing_total = league.roster_size - len(active_roster(team))
    if missing_total <= 0:
        raise BusinessRuleError("La rosa è già completa")

    pool = [p for p in worlds_player_pool(league.edition)
            if not player_taken_in_league(league.id, p.id)]
    for role in ROLE_ORDER:
        missing = league.max_per_role - counts.get(role.value, 0)
        candidates = [p for p in pool if p.ruolo == role.value]
        random.shuffle(candidates)
        if len(candidates) < missing:
            raise BusinessRuleError(
                f"Non ci sono abbastanza player disponibili nel ruolo {role.value}")
        for player in candidates[:missing]:
            WorldsRosterEntry.objects.create(fanta_team=team, player=player, crediti_spesi=0)
            pool.remove(player)
    return team


# --------------------------------------------------------------------------
# Sostituzioni fra fasi (jolly)
# --------------------------------------------------------------------------
@transaction.atomic
def swap_player(user, team_id, out_player_id, in_player_id, *, now=None) -> WorldsTeam:
    """Sostituzione libera fra una fase e l'altra.

    Consentita solo se `allow_reentry_swap` è attivo e la fase corrente non ha
    ancora bloccato le formazioni. Il player in entrata costa la sua quotazione,
    quello in uscita viene marcato come rilasciato dalla fase corrente (lo
    storico dei punti già maturati resta intatto).
    """
    team = get_team_or_404(team_id)
    assert_team_owner(user, team)
    league = team.league
    if not league.allow_reentry_swap:
        raise BusinessRuleError("Le sostituzioni fra fasi non sono abilitate in questa lega")

    now = now or timezone.now()
    stage = current_stage(league.edition, now=now)
    if stage is None:
        raise BusinessRuleError("Nessuna fase disponibile per la sostituzione")
    deadline = stage.effective_deadline()
    if stage.lineups_locked or (deadline is not None and deadline <= now):
        raise BusinessRuleError(
            f"La deadline della fase {stage.nome} è scaduta: la rosa è bloccata")

    entry = (WorldsRosterEntry.objects
             .select_related("player")
             .filter(fanta_team=team, player_id=out_player_id, released_at_stage__isnull=True)
             .first())
    if entry is None:
        raise BusinessRuleError("Il player da sostituire non è nella rosa attuale")

    incoming = ProPlayer.objects.select_for_update().filter(pk=in_player_id).first()
    if incoming is None:
        raise ResourceNotFound(f"Player non trovato con id: {in_player_id}")
    assert_eligible(league, incoming)
    if player_taken_in_league(league.id, incoming.id):
        raise BusinessRuleError("Il player in entrata è già assegnato in questa lega")
    if incoming.ruolo != entry.player.ruolo:
        raise BusinessRuleError("La sostituzione deve avvenire fra player dello stesso ruolo")
    if team.crediti_residui < incoming.quotazione:
        raise BusinessRuleError(
            f"Crediti insufficienti: servono {incoming.quotazione}, disponibili {team.crediti_residui}")

    entry.released_at_stage = stage
    entry.save(update_fields=["released_at_stage"])
    team.crediti_residui -= incoming.quotazione
    team.save(update_fields=["crediti_residui"])
    WorldsRosterEntry.objects.update_or_create(
        fanta_team=team, player=incoming,
        defaults={"crediti_spesi": incoming.quotazione, "acquired_from_stage": stage,
                  "released_at_stage": None})
    return team


# --------------------------------------------------------------------------
# Formazione per fase
# --------------------------------------------------------------------------
@transaction.atomic
def confirm_stage_lineup(user, team_id, stage_id, player_ids: list[int], *, now=None) -> WorldsStageLineup:
    """Conferma i 5 titolari (uno per ruolo) per una fase, entro la deadline."""
    team = get_team_or_404(team_id)
    assert_team_owner(user, team)
    stage = get_stage_or_404(stage_id)
    if stage.edition_id != team.league.edition_id:
        raise BusinessRuleError("La fase non appartiene all'edizione di questa lega")

    now = now or timezone.now()
    deadline = stage.effective_deadline()
    if stage.lineups_locked or (deadline is not None and deadline <= now):
        raise BusinessRuleError(
            f"La formazione per la fase {stage.nome} è chiusa (deadline: {deadline})")

    if len(player_ids) != NUMERO_TITOLARI or len(set(player_ids)) != NUMERO_TITOLARI:
        raise BusinessRuleError(f"Devi schierare esattamente {NUMERO_TITOLARI} titolari diversi")

    roster_ids = {entry.player_id: entry.player for entry in active_roster(team)}
    players = []
    for player_id in player_ids:
        player = roster_ids.get(player_id)
        if player is None:
            raise BusinessRuleError(
                f"Il player con id {player_id} non appartiene alla rosa di questa squadra")
        players.append(player)
    if len({p.ruolo for p in players}) != NUMERO_TITOLARI:
        raise BusinessRuleError("La formazione deve contenere esattamente un player per ruolo")

    lineup, _ = WorldsStageLineup.objects.get_or_create(fanta_team=team, stage=stage)
    lineup.titolari.set(players)
    lineup.confirmed = True
    lineup.confirmed_at = now
    lineup.save(update_fields=["confirmed", "confirmed_at"])
    recompute_stage_lineup(lineup)
    return lineup


def stage_lineup(team: WorldsTeam, stage: WorldsStage) -> WorldsStageLineup | None:
    return (WorldsStageLineup.objects.prefetch_related("titolari")
            .filter(fanta_team=team, stage=stage).first())


# --------------------------------------------------------------------------
# Punteggi e classifica
# --------------------------------------------------------------------------
def stage_player_scores(stage: WorldsStage, player_ids) -> dict[int, float]:
    """Fantapunti accumulati dai player nelle serie della fase."""
    totals: dict[int, float] = {}
    stats = (GamePlayerStat.objects
             .filter(game__match__worlds_stage=stage, player_id__in=list(player_ids))
             .select_related("player"))
    for stat in stats:
        if stat.participated:
            totals[stat.player_id] = totals.get(stat.player_id, 0.0) + stat.fantasy_score
    return totals


def recompute_stage_lineup(lineup: WorldsStageLineup) -> WorldsStageLineup:
    """Ricalcola punteggio e bonus di una formazione di fase."""
    players = list(lineup.titolari.select_related("team").all())
    scores = stage_player_scores(lineup.stage, [p.id for p in players])
    lineup.punteggio = sum(scores.get(p.id, 0.0) for p in players)
    lineup.bonus = bonuses.compute(lineup.stage, players, league=lineup.fanta_team.league).total
    lineup.save(update_fields=["punteggio", "bonus"])
    return lineup


def recompute_league(league: WorldsLeague) -> int:
    count = 0
    for lineup in (WorldsStageLineup.objects
                   .filter(fanta_team__league=league)
                   .select_related("stage", "stage__edition", "fanta_team", "fanta_team__league")):
        recompute_stage_lineup(lineup)
        count += 1
    return count


def standings(league: WorldsLeague) -> list[dict]:
    """Classifica Worlds: cumulativa per fase, con tie-break bonus -> fase più avanzata -> nome."""
    stages = list(league.edition.stages.all().order_by("ordine"))
    rows: list[dict] = []
    for team in league.teams.select_related("owner").all():
        per_stage = []
        total = 0.0
        bonus_total = 0.0
        for stage in stages:
            lineup = stage_lineup(team, stage)
            punteggio = lineup.punteggio if lineup else 0.0
            bonus = lineup.bonus if lineup else 0.0
            total += punteggio + bonus
            bonus_total += bonus
            per_stage.append({
                "stageId": stage.id,
                "stageNome": stage.nome,
                "ordine": stage.ordine,
                "confirmed": bool(lineup and lineup.confirmed),
                "punteggio": punteggio,
                "bonus": bonus,
                "totale": punteggio + bonus,
            })
        rows.append({
            "teamId": team.id,
            "teamNome": team.nome,
            "ownerUsername": team.owner.username,
            "creditiResidui": team.crediti_residui,
            "stages": per_stage,
            "bonusTotale": bonus_total,
            "totale": total,
        })

    def latest_stage_score(row: dict) -> float:
        """Punteggio nella fase più avanzata effettivamente disputata."""
        played = [s for s in row["stages"] if s["totale"] != 0.0]
        return played[-1]["totale"] if played else 0.0

    rows.sort(key=lambda row: (-row["totale"], -row["bonusTotale"],
                               -latest_stage_score(row), row["teamNome"]))
    for position, row in enumerate(rows, start=1):
        row["posizione"] = position
    return rows
