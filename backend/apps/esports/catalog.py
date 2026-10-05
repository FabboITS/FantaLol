"""Anagrafica pubblica di team e player per competizione/edizione (porting di ``LecTeamService`` e
``LecPlayerService``)."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import F, ProtectedError

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException
from apps.common.utils import now, role_index
from apps.competitions.models import Competition, CompetitionEdition

from .models import EditionRoster, ProPlayer, ProTeam


def editions_for(competition: str | None, edition_id: int | None) -> list[CompetitionEdition]:
    qs = CompetitionEdition.objects.select_related("competition")
    if edition_id is not None:
        edition = qs.filter(pk=edition_id).first()
        if edition is None:
            raise ResourceNotFoundException(f"Edizione non trovata con id: {edition_id}")
        return [edition]
    if competition:
        comp = Competition.objects.filter(code__iexact=competition).first()
        if comp is None:
            raise ResourceNotFoundException(f"Competizione non trovata: {competition}")
        current = comp.current_edition()
        return [current] if current else []
    result = []
    for comp in Competition.objects.all():
        current = comp.current_edition()
        if current is not None:
            result.append(current)
    return result


def player_item(entry: EditionRoster) -> dict:
    player, team = entry.player, entry.team
    return {
        "id": player.id,
        "nickname": player.nickname,
        "nome_reale": player.real_name or None,
        "nazionalita": player.nationality or None,
        "ruolo": entry.role,
        "quotazione": entry.quotazione,
        "team_id": team.id,
        "team_nome": team.name,
        "team_sigla": team.acronym,
        "team_logo_url": team.logo_url,
        "image_url": player.photo_url,
        "competition": entry.edition.competition.code,
        "edition_id": entry.edition_id,
        "is_starter": entry.is_starter,
    }


def roster_entries(editions: list[CompetitionEdition], role: str | None = None, team_id: int | None = None):
    qs = EditionRoster.objects.select_related("player", "team", "edition__competition").filter(
        edition__in=editions, active_to__isnull=True
    )
    if role:
        qs = qs.filter(role=role.upper())
    if team_id:
        qs = qs.filter(team_id=team_id)
    return sorted(
        qs,
        key=lambda e: (
            e.edition.competition.display_order,
            e.team.name.lower(),
            role_index(e.role),
            e.player.nickname.lower(),
        ),
    )


def list_players(
    competition: str | None, edition_id: int | None, role: str | None, team_id: int | None
) -> list:
    return [player_item(e) for e in roster_entries(editions_for(competition, edition_id), role, team_id)]


def team_item(team: ProTeam, entries: list[EditionRoster], edition: CompetitionEdition | None) -> dict:
    players = [player_item(e) for e in entries]
    return {
        "id": team.id,
        "nome": team.name,
        "sigla": team.acronym,
        "logo_url": team.logo_url,
        "competition": edition.competition.code if edition else None,
        "edition_id": edition.id if edition else None,
        "players": players,
        "giocatori": players,
    }


def list_teams(competition: str | None, edition_id: int | None) -> list[dict]:
    result = []
    for edition in editions_for(competition, edition_id):
        by_team: dict[int, list[EditionRoster]] = {}
        teams: dict[int, ProTeam] = {}
        for entry in roster_entries([edition]):
            by_team.setdefault(entry.team_id, []).append(entry)
            teams[entry.team_id] = entry.team
        for team_id in sorted(teams, key=lambda t: teams[t].name.lower()):
            result.append(team_item(teams[team_id], by_team[team_id], edition))
    return result


def get_team(team_id: int) -> ProTeam:
    team = ProTeam.objects.filter(pk=team_id).first()
    if team is None:
        raise ResourceNotFoundException(f"Team non trovato con id: {team_id}")
    return team


def team_detail(team_id: int, edition_id: int | None = None) -> dict:
    team = get_team(team_id)
    qs = EditionRoster.objects.select_related("player", "team", "edition__competition").filter(
        team=team, active_to__isnull=True
    )
    if edition_id is not None:
        qs = qs.filter(edition_id=edition_id)
    entries = sorted(qs, key=lambda e: (-e.edition.starts_at.timestamp(), role_index(e.role)))
    edition = entries[0].edition if entries else None
    return team_item(team, [e for e in entries if edition and e.edition_id == edition.id], edition)


@transaction.atomic
def create_team(data: dict) -> ProTeam:
    if ProTeam.objects.filter(name__iexact=data["nome"]).exists():
        raise BusinessRuleException(f"Esiste già un team con nome: {data['nome']}")
    return ProTeam.objects.create(
        name=data["nome"], acronym=data.get("sigla") or "", image_url_light=data.get("logo_url") or ""
    )


@transaction.atomic
def update_team(team_id: int, data: dict) -> ProTeam:
    team = get_team(team_id)
    team.name = data["nome"]
    team.acronym = data.get("sigla") or ""
    team.image_url_light = data.get("logo_url") or ""
    team.save()
    return team


def delete_team(team_id: int) -> None:
    team = get_team(team_id)
    try:
        team.delete()
    except (ProtectedError, IntegrityError):
        raise BusinessRuleException("Il team è collegato a dati di gioco e non può essere eliminato")


def team_summary(team: ProTeam) -> dict:
    return {"id": team.id, "nome": team.name, "sigla": team.acronym, "logo_url": team.logo_url}


def get_player(player_id: int) -> ProPlayer:
    player = ProPlayer.objects.filter(pk=player_id).first()
    if player is None:
        raise ResourceNotFoundException(f"Player non trovato con id: {player_id}")
    return player


def player_detail(player_id: int, edition_id: int | None = None) -> dict:
    player = get_player(player_id)
    qs = EditionRoster.objects.select_related("player", "team", "edition__competition").filter(player=player)
    if edition_id is not None:
        qs = qs.filter(edition_id=edition_id)
    entry = qs.order_by(F("active_to").desc(nulls_first=True), "-edition__starts_at", "-active_from").first()
    if entry is None:
        return {
            "id": player.id,
            "nickname": player.nickname,
            "nome_reale": player.real_name or None,
            "nazionalita": player.nationality or None,
            "ruolo": None,
            "quotazione": None,
            "team_id": None,
            "team_nome": None,
            "image_url": player.photo_url,
            "competition": None,
            "edition_id": None,
        }
    return player_item(entry)


def _edition_for_team(team: ProTeam, edition_id: int | None) -> CompetitionEdition:
    if edition_id is not None:
        edition = CompetitionEdition.objects.filter(pk=edition_id).first()
        if edition is None:
            raise ResourceNotFoundException(f"Edizione non trovata con id: {edition_id}")
        return edition
    entry = (
        EditionRoster.objects.select_related("edition")
        .filter(team=team, edition__is_active=True)
        .order_by("-edition__starts_at")
        .first()
    )
    if entry is not None:
        return entry.edition
    edition = CompetitionEdition.objects.filter(is_active=True).order_by("-starts_at").first()
    if edition is None:
        raise BusinessRuleException("Indica l'edizione (editionId) del player")
    return edition


@transaction.atomic
def create_player(data: dict) -> ProPlayer:
    team = get_team(data["team_id"])
    edition = _edition_for_team(team, data.get("edition_id"))
    player = ProPlayer.objects.create(
        nickname=data["nickname"],
        real_name=data.get("nome_reale") or "",
        nationality=data.get("nazionalita") or "",
        image_url=data.get("image_url") or "",
    )
    EditionRoster.objects.create(
        edition=edition,
        team=team,
        player=player,
        role=data["ruolo"],
        quotazione=data["quotazione"],
        quotazione_set_by_admin=True,
        active_from=edition.starts_at,
    )
    return player


@transaction.atomic
def update_player(player_id: int, data: dict) -> ProPlayer:
    player = get_player(player_id)
    team = get_team(data["team_id"])
    player.nickname = data["nickname"]
    player.real_name = data.get("nome_reale") or ""
    player.nationality = data.get("nazionalita") or ""
    player.image_url = data.get("image_url") or ""
    player.save()
    qs = EditionRoster.objects.filter(player=player, active_to__isnull=True)
    if data.get("edition_id"):
        qs = qs.filter(edition_id=data["edition_id"])
    entry = qs.select_related("edition").order_by("-edition__starts_at").first()
    if entry is None:
        edition = _edition_for_team(team, data.get("edition_id"))
        EditionRoster.objects.create(
            edition=edition,
            team=team,
            player=player,
            role=data["ruolo"],
            quotazione=data["quotazione"],
            quotazione_set_by_admin=True,
            active_from=edition.starts_at,
        )
    elif entry.team_id != team.id:
        entry.active_to = now()
        entry.save(update_fields=["active_to"])
        EditionRoster.objects.create(
            edition=entry.edition,
            team=team,
            player=player,
            role=data["ruolo"],
            quotazione=data["quotazione"],
            quotazione_set_by_admin=True,
            active_from=now(),
        )
    else:
        entry.role = data["ruolo"]
        entry.quotazione = data["quotazione"]
        entry.quotazione_set_by_admin = True
        entry.save(update_fields=["role", "quotazione", "quotazione_set_by_admin"])
    return player


def delete_player(player_id: int) -> None:
    player = get_player(player_id)
    try:
        with transaction.atomic():
            player.delete()
    except (ProtectedError, IntegrityError):
        raise BusinessRuleException("Il player appartiene a una rosa fantasy e non può essere eliminato")
