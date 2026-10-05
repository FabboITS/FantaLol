# ADR 0002 — Punteggio WORLDS come somma dei titolari

* **Stato:** Proposta (default applicato)
* **Contesto:** il regionale usa la media dei 5 slot (player senza statistiche = 0, diviso 5).
* **Decisione:** ai Worlds il punteggio di giornata è la **somma** dei 5 titolari effettivi (dopo le
  sostituzioni automatiche) + bonus capitano (punteggio del capitano × (moltiplicatore − 1), default
  ×2; se il capitano non gioca passa al vice) − penalità dei cambi della giornata. La classifica somma
  le giornate chiuse; spareggi: miglior giornata, punti totali dei capitani, data di iscrizione.
* **Motivazione:** con la somma il capitano pesa in modo percepibile (come nel Fantasy UCL); con la
  media il raddoppio varrebbe un quinto.
* **Configurazione:** `League.settings.captain_multiplier`.
