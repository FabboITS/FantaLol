# ADR 0008 — Deviazioni consapevoli dal backend Java

* **Stato:** Accettata
* **Codice HTTP delle regole di business:** il Java restituisce **422** per `BusinessRuleException`
  (non 400/409 come indicato nel prompt): si mantiene 422 per compatibilità con il frontend.
* **Prima giornata:** come nelle regole, solo la creazione della *prima* giornata congela i
  partecipanti e apre l'asta (il Java la riapriva a ogni nuova giornata).
* **Classifica regionale:** `/cumulative-ranking` porta 1:1 `CumulativeScoringService` (somma dei
  fantapunti per game attribuiti con lo storico dei titolari, provvisoria se uno slot non ha game);
  il punteggio di giornata (media dei 5 slot) viene salvato alla chiusura della giornata su
  `Formation.punteggio_totale` e la somma delle giornate chiuse è in `FantaTeam.punti`.
* **Sincronizzazione admin:** `POST /api/admin/competitions/{code}/synchronize` risponde 202 e
  delega allo scheduler: le view non chiamano mai i provider.
* **Giornate regionali:** una giornata copre una finestra temporale (di default la settimana di gioco
  della data indicata nel fuso della competizione); le serie della finestra alimentano i `PlayerStat`.
* **Endpoint `/api/players` e `/api/teams`:** senza filtri restituiscono le edizioni correnti di tutte
  le competizioni; il frontend filtra sempre per competizione/edizione.
* **Correzioni manuali:** oltre a correggere una riga esistente, l'override può creare statistiche
  per un player senza riga Leaguepedia (caso LPL).
