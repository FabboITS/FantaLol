# ADR 0005 — Rosa regionale con più di 10 team (LPL)

* **Stato:** Proposta (da confermare con il numero effettivo di team LPL dell'edizione)
* **Decisione:** con T = numero di team reali dell'edizione (calcolato dall'`EditionRoster` attivo):
  partecipanti ≤ floor(T/2) → rosa da 10 (2 per ruolo, 5 titolari + 5 riserve); altrimenti rosa da 5
  (1 per ruolo, formazione automatica). Massimo T partecipanti per lega.
* Per T = 10 il risultato coincide con la regola attuale (2–5 → 10 player; 6–10 → 5 player); test
  parametrici con T = 10, 14 e 16 in `backend/tests/test_roster_policy.py`.
* Se il roster dell'edizione non è ancora sincronizzato si usa T = 10.
