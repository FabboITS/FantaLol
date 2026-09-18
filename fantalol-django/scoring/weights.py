"""Coefficienti della formula fantapunti, per ruolo.

Valori ripresi **senza modifiche** dal backend Java originale,
`com.fantalol.backend.scoring.RoleScoreWeights` (record
`Weights(kills, assists, deaths, csPerHundred)`), oggi consultabile solo nella
storia dei commit.

    fantapunti = uccisioni x K(ruolo)
               + assist    x A(ruolo)
               - morti      x D(ruolo)
               + risorsa(ruolo)
               + 3 se vittoria

La "risorsa" vale `(cs / 100) * csPerHundred` per TOP/JUNGLE/MID/ADC e
`vision_score / 50` per il SUPPORT (cfr. `GameScoreCalculator.resourceScore`).
"""
from __future__ import annotations

from dataclasses import dataclass

from teams.models import PlayerRole


@dataclass(frozen=True)
class RoleWeights:
    kills: float
    assists: float
    deaths: float
    cs_per_hundred: float


ROLE_WEIGHTS: dict[str, RoleWeights] = {
    PlayerRole.TOP.value: RoleWeights(3.00, 2.00, 2.00, 1.25),
    PlayerRole.JUNGLE.value: RoleWeights(3.00, 2.25, 2.00, 0.70),
    PlayerRole.MID.value: RoleWeights(3.00, 2.00, 2.00, 1.00),
    PlayerRole.ADC.value: RoleWeights(3.25, 1.75, 2.25, 1.10),
    PlayerRole.SUPPORT.value: RoleWeights(2.15, 2.55, 1.75, 0.0),
}

#: Bonus vittoria, identico per tutti i ruoli.
WIN_BONUS = 3.0

#: Divisore del vision score per il SUPPORT.
SUPPORT_VISION_DIVISOR = 50.0


def weights_for(role: str) -> RoleWeights:
    try:
        return ROLE_WEIGHTS[role]
    except KeyError as exc:
        raise ValueError("Player role is required") from exc
