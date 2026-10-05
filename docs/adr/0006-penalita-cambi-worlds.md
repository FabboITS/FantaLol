# ADR 0006 — Cambi WORLDS: 2 gratuiti per giornata Swiss, extra −3 punti

* **Stato:** Proposta (default applicato)
* **Decisione:**
  * prima di G1 e prima di G6, G7, G8 (prima giornata di ogni fase con
    `Stage.free_transfers_unlimited_before`): cambi illimitati e gratuiti;
  * durante lo Swiss (G2–G5): 2 cambi gratuiti per giornata, non cumulabili; ogni cambio extra
    costa 3 punti, sottratti alla giornata su cui il cambio ha effetto;
  * vendere un player di una squadra eliminata (3 sconfitte Swiss, sconfitta a eliminazione diretta,
    non qualificata dal Play-In) è sempre gratuito e non consuma la quota;
  * si vende al prezzo di quotazione; si spendono solo i crediti disponibili (budget 100, +5 dalla
    fase a eliminazione diretta).
* **Configurazione:** `League.settings.free_transfers_per_matchday`, `extra_transfer_penalty`,
  `budget`; limiti per team e bonus budget in `Stage` (admin Django).
