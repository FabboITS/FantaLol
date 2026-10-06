# ADR 0007 — Statistiche LPL mancanti

* **Stato:** Proposta (default applicato)
* **Contesto:** Leaguepedia ha buchi nella LPL (righe `MISSING`, serie non trovate).
* **Decisione:** se dopo `LEAGUEPEDIA_GIVE_UP_DAYS` (7) giorni una serie è ancora scoperta viene tolta
  dalla coda di arricchimento; la giornata resta **provvisoria** (non si chiude automaticamente)
  finché l'admin non inserisce i dati: `POST /api/admin/esports/matches/{id}/games` (game manuale) e
  `PUT /api/admin/games/{gameId}/players/{playerId}` (statistiche). Le righe non associate si
  risolvono creando alias (`POST /api/admin/esports/aliases/{team|player}`), che ricollegano anche le
  righe già salvate.
* **Alternativa futura:** piano Historical di PandaScore come seconda fonte (a pagamento, ~400 €/mese).
