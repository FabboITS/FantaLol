"""Regolamento WORLDS: listone a prezzi fissi, limiti per team, cambi, capitano e sostituzioni automatiche."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum

from apps.common.exceptions import BusinessRuleException, ResourceNotFoundException
from apps.common.utils import ROLE_VALUES, now, role_index
from apps.competitions.models import CompetitionEdition, Stage, StageCode, ensure_worlds_stages
from apps.esports.models import EditionRoster, EsportsMatch, MatchStatus, ProPlayer
from apps.leagues import policy as roster_policy
from apps.leagues.models import FantaTeam, League, RosterEntry
from apps.leagues.services import assert_owner, edition_roster_map
from apps.lineups import services as lineups
from apps.matchdays.models import Formation, FormationSource, Matchday
from apps.scoring.formulas import matchday_score

from .models import Transfer

STAGE_LABELS = {
    StageCode.QUARTERFINALS: "Quarti di finale",
    StageCode.SEMIFINALS: "Semifinali",
    StageCode.FINAL: "Finale",
}
SWISS_ROUNDS = 5


# --------------------------------------------------------------------------- calendario
def _stages(edition: CompetitionEdition) -> dict[str, Stage]:
    ensure_worlds_stages(edition)
    return {s.code: s for s in edition.stages.all()}


def matchday_plan(edition: CompetitionEdition) -> list[dict]:
    """G1–G5 = Swiss Round 1–5, G6 = Quarti, G7 = Semifinali, G8 = Finale (il Play-In è escluso)."""
    stages = _stages(edition)
    matches = list(
        EsportsMatch.objects.filter(edition=edition, stage__isnull=False, begin_at__isnull=False)
        .exclude(status=MatchStatus.CANCELED)
        .select_related("stage")
        .prefetch_related("match_teams")
        .order_by("begin_at", "id")
    )
    rounds: dict[int, list[EsportsMatch]] = defaultdict(list)
    played: Counter = Counter()
    for match in (m for m in matches if m.stage.code == StageCode.SWISS):
        team_ids = [mt.team_id for mt in match.match_teams.all()]
        number = max((played[t] for t in team_ids), default=0) + 1
        for team_id in team_ids:
            played[team_id] += 1
        rounds[min(number, SWISS_ROUNDS)].append(match)
    groups: list[tuple[int, Stage, str, list[EsportsMatch]]] = []
    for number in range(1, SWISS_ROUNDS + 1):
        groups.append((number, stages[StageCode.SWISS], f"Swiss Round {number}", rounds.get(number, [])))
    for offset, code in enumerate((StageCode.QUARTERFINALS, StageCode.SEMIFINALS, StageCode.FINAL)):
        groups.append(
            (
                SWISS_ROUNDS + 1 + offset,
                stages[code],
                STAGE_LABELS[code],
                [m for m in matches if m.stage.code == code],
            )
        )
    plan = []
    for index, (numero, stage, label, group) in enumerate(groups):
        start = min((m.begin_at for m in group), default=None) or stage.starts_at
        later = [min(m.begin_at for m in g) for _, _, _, g in groups[index + 1 :] if g]
        if later:
            end = later[0]
        elif group:
            end = max(m.begin_at for m in group) + timedelta(days=1)
        else:
            end = stage.ends_at
        plan.append(
            {"numero": numero, "stage": stage, "descrizione": label, "starts_at": start, "ends_at": end}
        )
    return plan


@transaction.atomic
def generate_matchdays(league: League) -> list[Matchday]:
    """Crea o aggiorna le 8 giornate WORLDS della lega a partire dal calendario sincronizzato."""
    result = []
    for item in matchday_plan(league.edition):
        matchday, _ = Matchday.objects.get_or_create(
            league=league,
            numero=item["numero"],
            defaults={"descrizione": item["descrizione"], "stage": item["stage"]},
        )
        if not matchday.chiusa:
            matchday.descrizione = item["descrizione"]
            matchday.stage = item["stage"]
            matchday.starts_at = item["starts_at"]
            matchday.ends_at = item["ends_at"]
            matchday.data = item["starts_at"].date() if item["starts_at"] else None
            matchday.save()
        result.append(matchday)
    return result


def refresh_all_worlds_matchdays() -> int:
    count = 0
    for league in League.objects.filter(ruleset="WORLDS", participant_count__isnull=False):
        generate_matchdays(league)
        count += 1
    return count


def target_matchday(league: League) -> Matchday | None:
    """Prima giornata non ancora bloccata: è quella su cui agiscono formazione e cambi."""
    status = lineups.window_status(league)
    if status.target_matchday_id:
        return Matchday.objects.select_related("stage").get(pk=status.target_matchday_id)
    return None


def current_stage(league: League, matchday: Matchday | None = None) -> Stage | None:
    matchday = matchday if matchday is not None else target_matchday(league)
    if matchday is not None and matchday.stage_id:
        return matchday.stage
    stages = _stages(league.edition)
    played = (
        Matchday.objects.filter(league=league, starts_at__lte=now(), stage__isnull=False)
        .select_related("stage")
        .order_by("-numero")
        .first()
    )
    return played.stage if played else stages.get(StageCode.SWISS)


def _is_unlimited_window(league: League, matchday: Matchday | None) -> bool:
    if matchday is None:
        return True
    first_of_stage = not Matchday.objects.filter(
        league=league, stage_id=matchday.stage_id, numero__lt=matchday.numero
    ).exists()
    return bool(first_of_stage and matchday.stage and matchday.stage.free_transfers_unlimited_before)


# --------------------------------------------------------------------------- listone ed eliminazioni
def eliminated_teams(edition: CompetitionEdition) -> set[int]:
    eliminated: set[int] = set()
    swiss_losses: Counter = Counter()
    for match in (
        EsportsMatch.objects.filter(edition=edition, status=MatchStatus.FINISHED, stage__isnull=False)
        .select_related("stage")
        .prefetch_related("match_teams")
    ):
        losers = [
            mt.team_id
            for mt in match.match_teams.all()
            if match.winner_team_id and mt.team_id != match.winner_team_id
        ]
        if match.stage.code == StageCode.SWISS:
            swiss_losses.update(losers)
        elif match.stage.code in (StageCode.QUARTERFINALS, StageCode.SEMIFINALS, StageCode.FINAL):
            eliminated.update(losers)
    eliminated.update(team for team, losses in swiss_losses.items() if losses >= 3)
    if edition.listone_published_at:
        eliminated.update(
            EditionRoster.objects.filter(edition=edition, in_listone=False).values_list("team_id", flat=True)
        )
    return eliminated


def _play_in_teams(edition: CompetitionEdition) -> set[int]:
    return set(
        EsportsMatch.objects.filter(edition=edition, stage__code=StageCode.PLAY_IN).values_list(
            "match_teams__team_id", flat=True
        )
    ) - {None}


def market_entries(edition: CompetitionEdition) -> list[EditionRoster]:
    qs = EditionRoster.objects.select_related("player", "team").filter(
        edition=edition, active_to__isnull=True
    )
    if edition.listone_published_at:
        qs = qs.filter(in_listone=True)
    else:
        # Prima della pubblicazione si compra solo dalle squadre qualificate direttamente.
        qs = qs.exclude(team_id__in=_play_in_teams(edition))
    return list(qs.order_by("-quotazione", "player__nickname"))


@transaction.atomic
def publish_listone(edition_id: int) -> CompetitionEdition:
    edition = CompetitionEdition.objects.select_for_update().filter(pk=edition_id).first()
    if edition is None:
        raise ResourceNotFoundException(f"Edizione non trovata con id: {edition_id}")
    if edition.competition.ruleset != "WORLDS":
        raise BusinessRuleException("Il listone esiste solo per le edizioni WORLDS")
    swiss = set(
        EsportsMatch.objects.filter(edition=edition, stage__code=StageCode.SWISS).values_list(
            "match_teams__team_id", flat=True
        )
    ) - {None}
    if not swiss:
        raise BusinessRuleException(
            "Lo Swiss Stage non è ancora in calendario: impossibile pubblicare il listone"
        )
    roster = EditionRoster.objects.filter(edition=edition, active_to__isnull=True)
    roster.filter(team_id__in=swiss).update(in_listone=True)
    roster.exclude(team_id__in=swiss).update(in_listone=False)
    edition.listone_published_at = now()
    edition.save(update_fields=["listone_published_at"])
    return edition


@transaction.atomic
def set_price(player_id: int, quotazione: int, edition_id: int | None = None) -> EditionRoster:
    qs = EditionRoster.objects.select_related("edition", "player", "team").filter(
        player_id=player_id, active_to__isnull=True, edition__competition__ruleset="WORLDS"
    )
    if edition_id is not None:
        qs = qs.filter(edition_id=edition_id)
    entry = qs.order_by("-edition__starts_at").first()
    if entry is None:
        raise ResourceNotFoundException(f"Player {player_id} non presente nel listone Worlds")
    if entry.edition.listone_published_at:
        raise BusinessRuleException("Il listone è già pubblicato: i prezzi restano fissi per tutto il torneo")
    if not 5 <= quotazione <= 20:
        raise BusinessRuleException("La quotazione Worlds deve essere compresa tra 5 e 20 crediti")
    entry.quotazione = quotazione
    entry.quotazione_set_by_admin = True
    entry.save(update_fields=["quotazione", "quotazione_set_by_admin"])
    return entry


# --------------------------------------------------------------------------- crediti e mercato
def budget(league: League, matchday: Matchday | None = None) -> int:
    base = int(league.settings.get("budget", league.crediti_iniziali))
    stage = current_stage(league, matchday)
    if stage is None:
        return base
    bonus = (
        (
            Stage.objects.filter(edition=league.edition, order__lte=stage.order).aggregate(
                total=Sum("budget_bonus")
            )["total"]
        )
        or 0
    )
    return base + bonus


def roster_cost(team: FantaTeam) -> int:
    ids = list(team.rosa.values_list("player_id", flat=True))
    roster = edition_roster_map(team.league.edition_id, ids)
    return sum(roster[p].quotazione for p in ids if p in roster)


def available_credits(team: FantaTeam, matchday: Matchday | None = None) -> int:
    return budget(team.league, matchday) - roster_cost(team)


def market(league: League) -> dict:
    edition = CompetitionEdition.objects.select_related("competition").get(pk=league.edition_id)
    stage = current_stage(league)
    eliminated = eliminated_teams(edition)
    return {
        "league_id": league.id,
        "edition_id": edition.id,
        "listone_published": edition.listone_published_at is not None,
        "stage": stage.code if stage else None,
        "max_players_per_team": stage.max_players_per_team if stage else None,
        "budget": budget(league),
        "items": [
            {
                "id": entry.player_id,
                "nickname": entry.player.nickname,
                "ruolo": entry.role,
                "quotazione": entry.quotazione,
                "team_id": entry.team_id,
                "team_nome": entry.team.name,
                "team_sigla": entry.team.acronym,
                "image_url": entry.player.photo_url,
                "eliminated": entry.team_id in eliminated,
            }
            for entry in market_entries(edition)
        ],
    }


def transfer_response(transfer: Transfer) -> dict:
    return {
        "id": transfer.id,
        "fanta_team_id": transfer.fanta_team_id,
        "matchday_id": transfer.matchday_id,
        "player_out_id": transfer.player_out_id,
        "player_out_nickname": transfer.player_out.nickname if transfer.player_out else None,
        "player_in_id": transfer.player_in_id,
        "player_in_nickname": transfer.player_in.nickname if transfer.player_in else None,
        "price_out": transfer.price_out,
        "price_in": transfer.price_in,
        "is_free": transfer.is_free,
        "penalty_points": transfer.penalty_points,
        "created_at": transfer.created_at,
    }


def transfer_summary(team: FantaTeam) -> dict:
    league = team.league
    matchday = target_matchday(league)
    unlimited = _is_unlimited_window(league, matchday)
    free_quota = int(league.settings.get("free_transfers_per_matchday", 2))
    used = _counted_transfers(team, matchday) if matchday is not None and not unlimited else 0
    stage = current_stage(league, matchday)
    counts = Counter(
        entry.team_id
        for entry in edition_roster_map(
            league.edition_id, team.rosa.values_list("player_id", flat=True)
        ).values()
    )
    return {
        "target_matchday_id": matchday.id if matchday else None,
        "target_matchday_numero": matchday.numero if matchday else None,
        "unlimited": unlimited,
        "free_transfers": None if unlimited else free_quota,
        "free_transfers_remaining": None if unlimited else max(0, free_quota - used),
        "extra_transfer_penalty": float(league.settings.get("extra_transfer_penalty", 3)),
        "max_players_per_team": stage.max_players_per_team if stage else None,
        "players_per_team": [{"team_id": t, "count": c} for t, c in sorted(counts.items())],
        "credits": available_credits(team, matchday),
        "budget": budget(league, matchday),
        "items": [
            transfer_response(t)
            for t in Transfer.objects.filter(fanta_team=team)
            .select_related("player_in", "player_out")
            .order_by("-created_at", "-id")
        ],
    }


def _counted_transfers(team: FantaTeam, matchday: Matchday) -> int:
    """Cambi della giornata che consumano la quota gratuita (esclusi quelli per team eliminati)."""
    return Transfer.objects.filter(
        fanta_team=team, matchday=matchday, player_in__isnull=False, freed_by_elimination=False
    ).count()


def _check_composition(roles: list[str]) -> None:
    size = len(roles)
    if size > roster_policy.WORLDS_ROSTER_SIZE:
        raise BusinessRuleException(f"La rosa WORLDS ha al massimo {roster_policy.WORLDS_ROSTER_SIZE} player")
    missing_roles = [r for r in ROLE_VALUES if r not in roles]
    if roster_policy.WORLDS_ROSTER_SIZE - size < len(missing_roles):
        raise BusinessRuleException(
            "La rosa deve poter schierare un titolare per ogni ruolo: "
            + ", ".join(missing_roles)
            + " mancanti"
        )


@transaction.atomic
def make_transfer(user, team_id: int, player_out_id: int | None, player_in_id: int | None) -> Transfer:
    team = (
        FantaTeam.objects.select_for_update()
        .select_related("league__edition", "owner")
        .filter(pk=team_id)
        .first()
    )
    if team is None:
        raise ResourceNotFoundException(f"FantaTeam non trovata con id: {team_id}")
    assert_owner(team, user)
    league = team.league
    if not league.is_worlds:
        raise BusinessRuleException("I cambi di mercato sono disponibili solo nelle leghe WORLDS")
    if player_out_id is None and player_in_id is None:
        raise BusinessRuleException("Indica il player da vendere e/o quello da acquistare")
    edition = league.edition
    matchday = target_matchday(league)
    owned = {e.player_id: e for e in team.rosa.all()}
    roster = edition_roster_map(edition.id, list(owned) + [p for p in (player_in_id, player_out_id) if p])
    if player_out_id is not None and player_out_id not in owned:
        raise BusinessRuleException("Il player da vendere non è nella tua rosa")
    price_out = roster[player_out_id].quotazione if player_out_id in roster else 0
    price_in = 0
    if player_in_id is not None:
        if player_in_id in owned:
            raise BusinessRuleException("Il player è già nella tua rosa")
        listone = {e.player_id: e for e in market_entries(edition)}
        if player_in_id not in listone:
            raise BusinessRuleException("Il player non è acquistabile dal listone")
        price_in = listone[player_in_id].quotazione
    after = [pid for pid in owned if pid != player_out_id] + ([player_in_id] if player_in_id else [])
    _check_composition([roster[pid].role for pid in after if pid in roster])
    stage = current_stage(league, matchday)
    limit = stage.max_players_per_team if stage else None
    if player_in_id is not None and limit is not None:
        team_in = roster[player_in_id].team_id
        team_out = roster[player_out_id].team_id if player_out_id in roster else None
        count = sum(1 for pid in after if pid in roster and roster[pid].team_id == team_in)
        if count > limit and team_in != team_out:
            raise BusinessRuleException(
                f"Puoi avere al massimo {limit} player dello stesso team in questa fase"
            )
    if available_credits(team, matchday) + price_out - price_in < 0:
        raise BusinessRuleException("Crediti insufficienti")

    is_free, penalty = True, 0.0
    eliminated_out = player_out_id is not None and roster[player_out_id].team_id in eliminated_teams(edition)
    if (
        player_in_id is not None
        and matchday is not None
        and not _is_unlimited_window(league, matchday)
        and not eliminated_out
    ):
        if _counted_transfers(team, matchday) >= int(league.settings.get("free_transfers_per_matchday", 2)):
            is_free = False
            penalty = float(league.settings.get("extra_transfer_penalty", 3))

    if player_out_id is not None:
        owned[player_out_id].delete()
    if player_in_id is not None:
        RosterEntry.objects.create(
            fanta_team=team, league=league, player_id=player_in_id, crediti_spesi=price_in
        )
    transfer = Transfer.objects.create(
        fanta_team=team,
        matchday=matchday,
        player_out_id=player_out_id,
        player_in_id=player_in_id,
        price_out=price_out,
        price_in=price_in,
        is_free=is_free,
        penalty_points=penalty,
        freed_by_elimination=bool(eliminated_out and player_in_id),
    )
    if matchday is not None:
        _patch_formation(team, matchday, player_out_id, player_in_id, roster)
    team.crediti_residui = available_credits(team, matchday)
    team.save(update_fields=["crediti_residui"])
    return transfer


def _patch_formation(team, matchday, player_out_id, player_in_id, roster) -> None:
    formation = Formation.objects.filter(fanta_team=team, matchday=matchday).first()
    if formation is None or player_out_id is None:
        return
    titolari = set(formation.titolari.values_list("id", flat=True))
    if player_out_id in titolari:
        formation.titolari.remove(player_out_id)
        if (
            player_in_id
            and roster.get(player_in_id)
            and roster[player_in_id].role == roster[player_out_id].role
        ):
            formation.titolari.add(player_in_id)
    bench = [player_in_id if pid == player_out_id else pid for pid in formation.bench_order if pid]
    formation.bench_order = [pid for pid in bench if pid]
    if formation.capitano_id == player_out_id:
        formation.capitano_id = None
    if formation.vice_capitano_id == player_out_id:
        formation.vice_capitano_id = None
    formation.save()


# --------------------------------------------------------------------------- formazione
def formation_for(team: FantaTeam, matchday: Matchday) -> Formation | None:
    own = Formation.objects.filter(fanta_team=team, matchday=matchday).first()
    if own is not None and own.source != FormationSource.MISSING and own.titolari.exists():
        return own
    previous = (
        Formation.objects.filter(
            fanta_team=team,
            matchday__numero__lt=matchday.numero,
            source__in=[FormationSource.SUBMITTED, FormationSource.CARRIED],
        )
        .order_by("-matchday__numero")
        .first()
    )
    return previous


def _rows(team: FantaTeam, ids: list[int]) -> list[dict]:
    roster = edition_roster_map(team.league.edition_id, ids)
    players = {p.id: p for p in ProPlayer.objects.filter(pk__in=ids)}
    return [
        {
            "id": pid,
            "nickname": players[pid].nickname,
            "role": roster[pid].role if pid in roster else None,
            "team_id": roster[pid].team_id if pid in roster else None,
            "matchday_score": 0.0,
        }
        for pid in ids
        if pid in players
    ]


def worlds_lineup_response(team: FantaTeam) -> dict:
    status = lineups.window_status(team.league)
    matchday = (
        Matchday.objects.filter(pk=status.target_matchday_id).first() if status.target_matchday_id else None
    )
    formation = (
        formation_for(team, matchday)
        if matchday
        else (Formation.objects.filter(fanta_team=team).order_by("-matchday__numero").first())
    )
    starters = (
        sorted(formation.titolari.values_list("id", flat=True), key=lambda pid: pid) if formation else []
    )
    starter_rows = sorted(_rows(team, list(starters)), key=lambda r: role_index(r["role"] or ""))
    current = Matchday.objects.filter(league=team.league, starts_at__lte=now(), ends_at__gt=now()).first()
    effective = formation_for(team, current) if current else None
    return {
        "players": starter_rows,
        "bench": _rows(team, formation.bench_order if formation else []),
        "capitano_id": formation.capitano_id if formation else None,
        "vice_capitano_id": formation.vice_capitano_id if formation else None,
        "effective_players": _rows(team, list(effective.titolari.values_list("id", flat=True)))
        if effective
        else [],
        "editable": matchday is not None,
        "next_effective_at": status.next_effective_at,
        "lock_at": status.lock_at,
        "target_matchday_id": matchday.id if matchday else None,
        "reason": status.reason,
    }


@transaction.atomic
def save_lineup(user, team: FantaTeam, data: dict) -> dict:
    assert_owner(team, user)
    matchday = target_matchday(team.league)
    if matchday is None:
        raise BusinessRuleException("Nessuna giornata Worlds modificabile: calendario non ancora disponibile")
    titolari = list(data.get("titolari_ids") or [])
    bench = list(data.get("panchina_ids") or [])
    captain = data.get("capitano_id")
    vice = data.get("vice_capitano_id")
    owned = set(team.rosa.values_list("player_id", flat=True))
    if len(titolari) != 5 or len(set(titolari)) != 5:
        raise BusinessRuleException("Devi schierare esattamente 5 titolari diversi")
    if any(pid not in owned for pid in titolari + bench):
        raise BusinessRuleException("Formazione e panchina devono contenere solo player della tua rosa")
    roster = edition_roster_map(team.league.edition_id, titolari)
    if sorted(roster[p].role for p in titolari if p in roster) != sorted(ROLE_VALUES):
        raise BusinessRuleException(
            "La formazione deve contenere un titolare per ruolo: TOP, JUNGLE, MID, ADC e SUPPORT"
        )
    if set(bench) & set(titolari) or len(set(bench)) != len(bench):
        raise BusinessRuleException("La panchina non può contenere titolari o player ripetuti")
    remaining = [pid for pid in owned if pid not in titolari]
    bench += [pid for pid in remaining if pid not in bench]
    if captain is None or captain not in titolari or vice is None or vice not in titolari or captain == vice:
        raise BusinessRuleException("Capitano e vice-capitano devono essere due titolari diversi")
    formation, _ = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
    formation.source = FormationSource.SUBMITTED
    formation.bench_order = bench
    formation.capitano_id = captain
    formation.vice_capitano_id = vice
    formation.save()
    formation.titolari.set(titolari)
    return worlds_lineup_response(team)


# --------------------------------------------------------------------------- chiusura giornata
def _player_scores(matchday: Matchday) -> dict[int, float]:
    from apps.matchdays.scoring import matchday_observations

    by_player: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for obs in matchday_observations(matchday):
        if obs.score is not None:
            by_player[obs.player_id][obs.match_id].append(obs.score)
    return {pid: matchday_score(series.values()) for pid, series in by_player.items()}


def score_formation(
    starters: list[int],
    bench: list[int],
    captain: int | None,
    vice: int | None,
    roles: dict[int, str],
    scores: dict[int, float],
    multiplier: float = 2.0,
) -> dict:
    """Sostituzioni automatiche (solo pari ruolo, in ordine di panchina) e bonus capitano."""
    used: set[int] = set()
    effective: list[dict] = []
    for pid in sorted(starters, key=lambda p: role_index(roles.get(p, ""))):
        if pid in scores:
            effective.append(
                {"id": pid, "role": roles.get(pid), "score": scores[pid], "substituted_for": None}
            )
            continue
        sub = next(
            (b for b in bench if b not in used and b in scores and roles.get(b) == roles.get(pid)), None
        )
        if sub is not None:
            used.add(sub)
            effective.append(
                {"id": sub, "role": roles.get(sub), "score": scores[sub], "substituted_for": pid}
            )
        else:
            effective.append({"id": pid, "role": roles.get(pid), "score": 0.0, "substituted_for": None})
    total = sum(item["score"] for item in effective)
    captain_points, bonus, doubled = 0.0, 0.0, None
    for candidate in (captain, vice):
        if candidate is not None and candidate in scores and any(e["id"] == candidate for e in effective):
            doubled = candidate
            bonus = scores[candidate] * (multiplier - 1)
            captain_points = scores[candidate] * multiplier
            break
    return {
        "effective": effective,
        "base": total,
        "bonus": bonus,
        "captain_points": captain_points,
        "doubled": doubled,
    }


def close_matchday(matchday: Matchday) -> None:
    league = matchday.league
    scores = _player_scores(matchday)
    multiplier = float(league.settings.get("captain_multiplier", 2))
    for team in league.fanta_teams.all():
        penalties = (
            (
                Transfer.objects.filter(fanta_team=team, matchday=matchday).aggregate(
                    total=Sum("penalty_points")
                )["total"]
            )
            or 0.0
        )
        source = formation_for(team, matchday)
        formation, _ = Formation.objects.get_or_create(fanta_team=team, matchday=matchday)
        if source is None:
            formation.source = FormationSource.MISSING
            formation.punteggio_totale = -penalties
            formation.penalty_points = penalties
            formation.save()
            continue
        starters = list(source.titolari.values_list("id", flat=True))
        if source.pk != formation.pk:
            formation.source = FormationSource.CARRIED
            formation.bench_order = source.bench_order
            formation.capitano_id = source.capitano_id
            formation.vice_capitano_id = source.vice_capitano_id
            formation.save()
            formation.titolari.set(starters)
        roles = {
            pid: e.role
            for pid, e in edition_roster_map(
                league.edition_id, starters + list(formation.bench_order)
            ).items()
        }
        result = score_formation(
            starters,
            list(formation.bench_order),
            formation.capitano_id,
            formation.vice_capitano_id,
            roles,
            scores,
            multiplier,
        )
        formation.effective_titolari = result["effective"]
        formation.captain_points = result["captain_points"]
        formation.penalty_points = penalties
        formation.punteggio_totale = result["base"] + result["bonus"] - penalties
        formation.save()


# --------------------------------------------------------------------------- classifica
def ranking(league: League) -> list[dict]:
    rows = []
    for team in league.fanta_teams.select_related("owner").order_by("id"):
        closed = list(
            Formation.objects.filter(fanta_team=team, matchday__chiusa=True)
            .select_related("matchday")
            .order_by("matchday__numero")
        )
        totals = [f.punteggio_totale or 0.0 for f in closed]
        rows.append(
            {
                "fantasy_team_id": team.id,
                "team_name": team.nome,
                "owner_username": team.owner.username,
                "overall_total": sum(totals),
                "best_matchday": max(totals) if totals else 0.0,
                "captain_points": sum(f.captain_points or 0.0 for f in closed),
                "joined_at": team.created_at,
                "matchdays": [{"numero": f.matchday.numero, "punti": f.punteggio_totale} for f in closed],
                "provisional": any(f.matchday.provisional for f in closed) or not closed,
                "slots": [],
            }
        )
    rows.sort(key=lambda r: (-r["overall_total"], -r["best_matchday"], -r["captain_points"], r["joined_at"]))
    return rows
