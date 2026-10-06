# ADR 0004 — Finestre di formazione per LCK, LPL e WORLDS

* **Stato:** Proposta (da verificare sui calendari ufficiali 2027 quando pubblicati)
* **Contesto:** la finestra LEC (mar 00:00 – gio 23:59:59 Europe/Rome, effettiva dal venerdì) si
  adatta al calendario LEC; LCK e LPL giocano su più giorni della settimana.
* **Decisione:** `LineupPolicy` configurabile per `CompetitionEdition` con due strategie:
  * `FIXED_WEEKLY_WINDOW(open_day, close_day, effective_day, timezone)` — default LEC;
  * `LOCK_BEFORE_FIRST_MATCH(lock_minutes=60)` — default LCK, LPL e WORLDS: la formazione della
    giornata è modificabile fino a 60 minuti prima della prima serie (calcolata dai match PandaScore);
    le modifiche successive valgono dalla giornata seguente. La "giornata" è la finestra della
    `Matchday` della lega o, se non ci sono giornate, la settimana lunedì→lunedì nel fuso della
    competizione.
* Le date sono salvate in UTC; il fuso (`Europe/Rome`, `Asia/Seoul`, `Asia/Shanghai`) serve solo al
  calcolo delle finestre (test con cambio dell'ora legale).
* **TODO dati:** l'ID PandaScore della lega WORLDS non è nel seed: si ricava con
  `python manage.py resolve_pandascore_leagues` (o automaticamente al primo sync). Gli
  `overview page` Leaguepedia non sono necessari (la ricerca dei game usa team + finestra temporale)
  e restano un campo opzionale dell'edizione.
