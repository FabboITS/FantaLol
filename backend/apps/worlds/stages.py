"""Riconoscimento della fase Worlds dai nomi di torneo/match PandaScore."""

from __future__ import annotations

import re

from apps.competitions.models import StageCode

_MATCH_PATTERNS = [
    (re.compile(r"quarter", re.I), StageCode.QUARTERFINALS),
    (re.compile(r"semi", re.I), StageCode.SEMIFINALS),
    (re.compile(r"(grand\s*final|^final\b|\bfinals?\s*:)", re.I), StageCode.FINAL),
]
_TOURNAMENT_PATTERNS = [
    (re.compile(r"play[\s-]?in", re.I), StageCode.PLAY_IN),
    (re.compile(r"swiss|group|main\s*event\s*-\s*swiss", re.I), StageCode.SWISS),
    (re.compile(r"quarter", re.I), StageCode.QUARTERFINALS),
    (re.compile(r"semi", re.I), StageCode.SEMIFINALS),
    (re.compile(r"^final", re.I), StageCode.FINAL),
]
_KNOCKOUT = re.compile(r"knockout|playoff|bracket|elimination", re.I)


def detect_stage_code(tournament_name: str | None, match_name: str | None) -> str | None:
    """Ritorna il codice della fase o ``None`` se non riconosciuta (il match si salva con stage nullo)."""
    tournament = tournament_name or ""
    match = match_name or ""
    for pattern, code in _TOURNAMENT_PATTERNS:
        if pattern.search(tournament):
            if code in (StageCode.PLAY_IN, StageCode.SWISS):
                return code
            break
    if (
        _KNOCKOUT.search(tournament)
        or not tournament
        or any(p.search(tournament) for p, _ in _TOURNAMENT_PATTERNS)
    ):
        for pattern, code in _MATCH_PATTERNS:
            if pattern.search(match):
                return code
        for pattern, code in _TOURNAMENT_PATTERNS:
            if pattern.search(tournament):
                return code
    return None
