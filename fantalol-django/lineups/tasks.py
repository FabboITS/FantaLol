"""Task Celery Beat: congela le formazioni pianificate quando scade la finestra."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="lineups.tasks.apply_due_lineup_windows")
def apply_due_lineup_windows() -> int:
    """Chiude i periodi la cui `valid_from` è ormai passata.

    Il congelamento è implicito nel modello (un periodo con `valid_from` nel
    passato è già attivo), quindi il task si limita a normalizzare eventuali
    periodi pendenti sovrapposti, così lo storico resta coerente.
    """
    from .models import LineupPeriod

    now = timezone.now()
    fixed = 0
    started = (LineupPeriod.objects
               .filter(valid_to__isnull=True, valid_from__lte=now)
               .select_related("fanta_team")
               .order_by("fanta_team_id", "role", "valid_from"))
    seen: dict[tuple[int, str], LineupPeriod] = {}
    for period in started:
        key = (period.fanta_team_id, period.role)
        previous = seen.get(key)
        if previous is not None and previous.valid_from < period.valid_from:
            previous.valid_to = period.valid_from
            previous.save(update_fields=["valid_to"])
            fixed += 1
        seen[key] = period
    if fixed:
        logger.info("Periodi di formazione normalizzati: %s", fixed)
    return fixed
