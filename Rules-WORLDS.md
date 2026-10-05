# Regole FantaLeague — WORLDS

Regolamento per le leghe sul World Championship, ispirato al FantaChampions / Fantasy UCL e adattato
a League of Legends. Tutti i numeri sono valori di default configurabili nelle impostazioni della
lega (`League.settings`) e nelle fasi dell'edizione.

## Principi

* **Listone a prezzi fissi, nessuna esclusività:** ogni partecipante compra liberamente con un budget;
  lo stesso player può stare in più fantasy team. Niente asta. Da 2 a 50 partecipanti per lega.
* **Limite di player dello stesso team reale**, crescente con l'avanzare del torneo.
* **Budget che cresce** dopo lo Swiss Stage.
* **Cambi illimitati** a inizio torneo e a ogni passaggio di fase, limitati durante lo Swiss.
* **Capitano** con punteggio doppio, vice-capitano di riserva, **sostituzioni automatiche** dalla
  panchina.
* **Play-In escluso:** serve solo a definire il listone, come i preliminari di Champions.

## Rosa e listone

* Rosa da **8 player**: 5 titolari (uno per ruolo TOP/JUNGLE/MID/ADC/SUPPORT) e 3 panchinari di
  ruolo libero, ordinati.
* **Budget iniziale 100 crediti**, **+5 crediti** dopo lo Swiss Stage (105 in totale).
* Il listone contiene i player delle 16 squadre dello Swiss Stage e viene pubblicato al termine del
  Play-In; prima della pubblicazione la rosa si compone solo con le squadre qualificate direttamente.
* **Quotazioni** da 5 a 20 crediti, fisse per tutto il torneo. Il calcolo iniziale
  (`compute_worlds_prices`) usa la media fantapunti per game della stagione regionale dello stesso
  anno, normalizzata per ruolo e mappata linearmente su 5–20; chi non ha dati regionali riceve il
  prezzo mediano del ruolo. L'amministratore può correggere le quotazioni prima della pubblicazione.

## Limite di player per team reale

| Fase | Max player dello stesso team |
| --- | --- |
| Swiss Stage | 2 |
| Quarti di finale | 3 |
| Semifinali | 4 |
| Finale | 5 |

Il limite è verificato a ogni cambio. Ai passaggi di fase una rosa che non lo rispetta più non viene
invalidata, ma non può fare cambi che peggiorino la violazione.

## Giornate

| Giornata | Contenuto |
| --- | --- |
| G1–G5 | Swiss Round 1 … Round 5 |
| G6 | Quarti di finale |
| G7 | Semifinali |
| G8 | Finale |

Ogni giornata contiene al massimo una serie per team reale: il punteggio di un player è la media dei
game da lui giocati in quella serie (formula regionale invariata, per Bo1/Bo3/Bo5). Nello Swiss le
squadre già qualificate (3-0) o eliminate (0-3) non giocano i round successivi: i loro player fanno 0.

## Formazione, capitano e sostituzioni automatiche

* Fino a 60 minuti prima della prima serie della giornata scegli i 5 titolari, l'ordine dei 3
  panchinari, capitano e vice-capitano tra i titolari. Le modifiche successive valgono dalla
  giornata seguente.
* **Sostituzioni automatiche:** a fine giornata ogni titolare che non ha giocato è sostituito dal
  primo panchinaro **dello stesso ruolo** che ha giocato, nell'ordine di panchina.
* **Capitano:** punteggio ×2. Se il capitano non gioca il raddoppio passa al vice; se nessuno dei due
  gioca, nessun raddoppio.
* Se un partecipante non schiera nulla resta valida l'ultima formazione salvata.

## Cambi

* Prima di G1: illimitati e gratuiti.
* Durante lo Swiss (G2–G5): **2 cambi gratuiti per giornata**, non cumulabili; ogni cambio extra
  costa **−3 punti** sulla giornata.
* Prima di G6, G7 e G8: illimitati e gratuiti.
* Un cambio che sostituisce un player il cui team è stato eliminato è sempre gratuito.
* Vendita al prezzo di quotazione; si possono spendere solo i crediti disponibili.

## Punteggio e classifica

* Punteggio di giornata = **somma** dei punteggi dei 5 titolari effettivi (dopo le sostituzioni) +
  bonus capitano − penalità dei cambi della giornata.
* Classifica generale = somma delle giornate chiuse. Spareggi: 1) miglior singola giornata,
  2) totale punti dei capitani, 3) data di iscrizione.
* Provvisorietà, rinvii e correzioni manuali funzionano come nel regolamento regionale.

Le motivazioni delle scelte sono nelle ADR `docs/adr/0001`–`0003` e `0006`.
