"""Registrazione dello stato dei provider (porting di ``ProviderSyncStateService``)."""

from __future__ import annotations

from django.db import transaction

from apps.common.utils import now
from apps.esports.models import ProviderSyncState


def _state(provider: str, competition) -> ProviderSyncState:
    state, _ = ProviderSyncState.objects.get_or_create(provider=provider, competition=competition)
    return state


@transaction.atomic
def record_success(
    provider: str,
    competition,
    *,
    error: str = "",
    counts: dict | None = None,
    unmatched: list[str] | None = None,
) -> ProviderSyncState:
    moment = now()
    state = _state(provider, competition)
    state.status = "SUCCESS"
    state.last_attempt_at = moment
    state.last_success_at = moment
    state.last_error = error[:1000]
    if counts is not None:
        state.inserted_games = counts.get("inserted", 0)
        state.updated_games = counts.get("updated", 0)
        state.skipped_games = counts.get("skipped", 0)
        state.failed_games = counts.get("failed", 0)
    if unmatched is not None:
        state.unmatched_players = sorted(set(unmatched))
    state.save()
    return state


@transaction.atomic
def record_failure(provider: str, competition, error: BaseException | str) -> ProviderSyncState:
    state = _state(provider, competition)
    message = str(error) or error.__class__.__name__
    state.status = "FAILED"
    state.last_attempt_at = now()
    state.last_error = message[:1000]
    state.save()
    return state


def request_sync(competition) -> None:
    for provider in ("PANDASCORE", "LEAGUEPEDIA"):
        state = _state(provider, competition)
        state.sync_requested_at = now()
        state.save(update_fields=["sync_requested_at"])
