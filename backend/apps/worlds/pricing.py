"""Quotazioni iniziali del listone Worlds (comando ``compute_worlds_prices``).

Media fantapunti per game della stagione regionale dello stesso anno (formula REGIONAL_V1, dati
Leaguepedia), normalizzata per ruolo e mappata linearmente su 5–20 crediti; per i player senza dati
regionali (es. LCS/LCP/CBLOL non coperti) si usa il prezzo mediano del ruolo.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from django.db import transaction

from apps.common.exceptions import BusinessRuleException
from apps.competitions.models import CompetitionEdition, Ruleset
from apps.esports.models import EditionRoster, EsportsGame
from apps.esports.observations import observations

MIN_PRICE = 5
MAX_PRICE = 20


def scale(value: float, low: float, high: float) -> int:
    if high <= low:
        return round((MIN_PRICE + MAX_PRICE) / 2)
    return round(MIN_PRICE + (value - low) / (high - low) * (MAX_PRICE - MIN_PRICE))


def regional_averages(year: int, player_ids) -> dict[int, float]:
    games = EsportsGame.objects.filter(
        match__edition__competition__ruleset=Ruleset.REGIONAL, match__edition__year=year
    )
    scores: dict[int, list[float]] = defaultdict(list)
    for obs in observations(games, player_ids=list(player_ids)):
        if obs.score is not None:
            scores[obs.player_id].append(obs.score)
    return {pid: sum(values) / len(values) for pid, values in scores.items()}


@transaction.atomic
def compute_prices(edition: CompetitionEdition, *, force: bool = False) -> dict:
    if edition.competition.ruleset != Ruleset.WORLDS:
        raise BusinessRuleException("Le quotazioni automatiche valgono solo per le edizioni WORLDS")
    if edition.listone_published_at and not force:
        raise BusinessRuleException("Listone già pubblicato: le quotazioni restano fisse")
    entries = list(EditionRoster.objects.filter(edition=edition, active_to__isnull=True))
    averages = regional_averages(edition.year, [e.player_id for e in entries])
    by_role: dict[str, list[EditionRoster]] = defaultdict(list)
    for entry in entries:
        by_role[entry.role].append(entry)
    report = {"priced": 0, "median_fallback": 0, "kept_admin": 0}
    for role_entries in by_role.values():
        known = [averages[e.player_id] for e in role_entries if e.player_id in averages]
        low, high = (min(known), max(known)) if known else (0.0, 0.0)
        prices = {
            e.player_id: scale(averages[e.player_id], low, high)
            for e in role_entries
            if e.player_id in averages
        }
        fallback = round(median(prices.values())) if prices else round((MIN_PRICE + MAX_PRICE) / 2)
        for entry in role_entries:
            if entry.quotazione_set_by_admin and not force:
                report["kept_admin"] += 1
                continue
            if entry.player_id in prices:
                entry.quotazione = prices[entry.player_id]
                report["priced"] += 1
            else:
                entry.quotazione = fallback
                report["median_fallback"] += 1
            entry.save(update_fields=["quotazione"])
    return report
