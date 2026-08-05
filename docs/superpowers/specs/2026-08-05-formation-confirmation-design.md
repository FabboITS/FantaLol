# Conferma formazione per giornata

## Obiettivo

Eliminare lo stato ambiguo “Formazione provvisoria” per le leghe con almeno sei fantasy team introducendo una conferma esplicita della rosa schierata. La conferma deve diventare parte dello stato persistente della formazione della singola giornata e deve essere utilizzabile anche quando non sono state effettuate sostituzioni.

## Comportamento

- Il manager apre `Giornate → Rosa` e vede la rosa attuale della propria squadra.
- Da martedì alle 00:00 a giovedì alle 23:59 è disponibile il pulsante `Conferma rosa`.
- La prima conferma salva, per la giornata selezionata, lo snapshot dei cinque titolari (uno per ruolo) e marca la formazione come confermata.
- Una formazione già confermata mostra `Formazione confermata` fuori dalla finestra di modifica.
- Se la rosa cambia, il manager può confermare nuovamente nella finestra successiva. La nuova conferma sostituisce lo snapshot della giornata e vale per il periodo successivo, senza modificare i punteggi dei periodi passati.
- Da venerdì a lunedì la conferma è bloccata, come le altre modifiche alla formazione.
- Il pulsante di conferma del manager è visibile solo al proprietario della fantasy team (oltre all’ADMIN secondo le normali regole di gestione).

## Amministrazione globale

- Sotto ogni giornata, nell’area `Amministrazione globale`, l’utente con ruolo `ADMIN` vede `Conferma tutte le squadre`.
- Il comando è disponibile soltanto nella finestra martedì–giovedì.
- Il comando conferma lo snapshot corrente per tutte le fantasy team della lega; è idempotente e può essere ripetuto senza creare duplicati.
- L’endpoint deve verificare il ruolo globale `ADMIN`, la giornata e la finestra temporale lato server; la visibilità del pulsante lato client non è una misura di sicurezza.

## Modello e API

- Aggiungere a `Formation` un campo persistente `confirmed` (default `false`) e la relativa esposizione nei DTO.
- La conferma del manager aggiorna o crea la formazione della giornata con i titolari correnti e `confirmed=true`, mantenendo la normale validazione dei cinque ruoli.
- Aggiungere un endpoint autenticato per confermare la formazione della propria fantasy team per una giornata.
- Aggiungere un endpoint autenticato riservato ad `ADMIN` per confermare in massa tutte le fantasy team della lega per una giornata.
- Le conferme devono aggiornare i periodi di lineup futuri senza riscrivere periodi già conclusi.

## Frontend

- Inserire il pulsante e lo stato nella sezione Rosa del dialogo/formazione associato alle giornate.
- Aggiornare lo stato dopo la conferma e mostrare un messaggio di successo o errore.
- Nella sezione amministrativa di ogni giornata mostrare il pulsante solo agli ADMIN e ricaricare giornate, formazioni e classifica dopo l’operazione.

## Test e criteri di accettazione

- Una lega da otto squadre può confermare la rosa automatica senza sostituzioni.
- La conferma è rifiutata fuori dalla finestra martedì–giovedì anche se si invoca direttamente l’API.
- Una seconda conferma dopo una modifica aggiorna solo il periodo futuro.
- Un utente non ADMIN riceve errore di autorizzazione sull’endpoint globale e non vede il pulsante.
- La conferma globale aggiorna tutte le squadre della giornata ed è ripetibile.
- Una formazione confermata non viene più indicata come provvisoria nella classifica, salvo l’assenza effettiva di statistiche partita.
