# FantaLeague React

Replica moderna in React del frontend FantaLeague già presente nel repository. Questa
applicazione vive nella cartella `fantalol-react` ed è completamente separata da
`fantalol-frontend`: il frontend originale non viene modificato né richiesto per avviare
questa versione.

FantaLeague è un fantasy game dedicato alla LEC, il campionato EMEA di League of
Legends. Gli utenti possono consultare i giocatori, creare o raggiungere leghe private,
comporre una rosa tramite asta a crediti e seguire classifica e giornate.

## Funzionalità disponibili

- home page responsive con presentazione e regolamento sintetico;
- catalogo giocatori con ricerca e filtro per ruolo;
- registrazione e login;
- rotte protette per l'area privata;
- elenco, creazione e partecipazione alle leghe;
- dashboard della lega con classifica, rose, mercato e giornate;
- tema chiaro/scuro persistente;
- modalità demo locale persistente, senza backend;
- collegamento opzionale al backend Spring Boot incluso nel repository;
- pagina 404 e stati di caricamento/errore;
- layout responsive e supporto a `prefers-reduced-motion`.

## Tecnologie

- [React 18](https://react.dev/)
- [Vite](https://vite.dev/)
- [React Router](https://reactrouter.com/)
- [Material UI](https://mui.com/material-ui/)
- [Vitest](https://vitest.dev/)
- Testing Library
- ESLint

La gestione del login usa `AuthContext`; il tema usa un secondo context dedicato.
Le pagine usano `useState`, `useEffect`, `useMemo` e `useCallback` per stato,
caricamento dati, filtri e operazioni utente.

## Prerequisiti

Per la modalità demo sono necessari:

- Git;
- Node.js 20 LTS o successivo;
- npm 10 o successivo.

Controllare le versioni installate:

```bash
node --version
npm --version
```

## Avvio rapido: modalità demo

La modalità demo è il modo consigliato per provare subito l'interfaccia. Non richiede
Java, MySQL, Docker, chiavi API o dati da importare.

```bash
git clone <URL-DEL-REPOSITORY>
cd FantaLolFabrizio/fantalol-react
npm install
cp .env.example .env
npm run dev
```

Aprire `http://localhost:5173`.

Credenziali già disponibili:

```text
username: demo
password: demo123
```

È disponibile anche un account amministratore dimostrativo:

```text
username: admin
password: admin123
```

In alternativa è possibile registrare un nuovo utente. Utenti, leghe e fantasy team
creati in modalità demo vengono conservati nel `localStorage` del browser. Il pulsante
“Reset demo” nella barra superiore elimina i dati demo e ripristina lo stato iniziale.

> La modalità demo è esclusivamente didattica: le password vengono conservate in chiaro
> nel browser e non deve essere utilizzata in produzione.

## Collegamento al backend Spring Boot

Il frontend può usare le API reali già presenti in `fantalol-backend`. Prima avviare
l'intero stack dalla root del repository:

```bash
docker compose -f fantalol-backend/docker-compose.yml up --build
```

Il backend sarà raggiungibile su `http://localhost:8080` e MySQL sulla porta host
`3307`. Per tutti i dettagli, incluse variabili database, JWT e PandaScore, consultare
il [README principale](../README.md).

Creare quindi `fantalol-react/.env`:

```env
VITE_API_BASE_URL=http://localhost:8080
```

Infine avviare il frontend:

```bash
cd fantalol-react
npm install
npm run dev
```

Le variabili Vite vengono lette solo all'avvio: dopo una modifica a `.env` bisogna
riavviare `npm run dev`. Non inserire token o segreti in variabili con prefisso
`VITE_`, perché vengono inclusi nel JavaScript inviato al browser.

Se `VITE_API_BASE_URL` è vuota o assente, l'applicazione usa automaticamente la
modalità demo. Durante lo sviluppo è anche configurato un proxy Vite da `/api` a
`http://localhost:8080`.

## Comandi disponibili

```bash
npm run dev       # server di sviluppo con hot reload
npm run build     # build ottimizzata nella cartella dist/
npm run preview   # anteprima locale della build
npm run lint      # controllo statico ESLint
npm test          # test automatici in modalità non interattiva
```

Prima di aprire una pull request:

```bash
npm run lint
npm test
npm run build
```

## Struttura del progetto

```text
fantalol-react/
├── public/                 asset pubblici
├── src/
│   ├── components/         componenti riutilizzabili e test
│   ├── context/            autenticazione e tema
│   ├── data/               dataset iniziale della modalità demo
│   ├── pages/              pagine collegate a React Router
│   ├── services/           API HTTP e API demo
│   ├── styles/             stile globale responsive
│   ├── test/               configurazione Vitest
│   ├── App.jsx             albero delle rotte
│   └── main.jsx            entry point React
├── .env.example
├── eslint.config.js
├── package.json
└── vite.config.js
```

`public/Player_immage` è un collegamento simbolico alla cartella
`../fantalol-frontend/Player_immage`. In questo modo la replica React riutilizza i
ritratti già presenti nel repository senza duplicarli e senza modificare il frontend
originale. Conservare la struttura delle due cartelle quando si clona o si sposta il
progetto.

## Rotte

| Rotta | Accesso | Contenuto |
|---|---|---|
| `/` | pubblico | home e introduzione |
| `/players` | pubblico | catalogo e filtri giocatori |
| `/login` | pubblico | login e registrazione |
| `/leagues` | autenticato | leghe dell'utente |
| `/leagues/:leagueId` | autenticato | dashboard di una lega |
| `*` | pubblico | pagina 404 |

Una rotta privata richiesta senza sessione reindirizza a `/login` e, dopo il login,
riporta l'utente alla pagina inizialmente richiesta.

## Modalità dati

`src/services/api.js` offre un'unica interfaccia alle pagine:

- senza `VITE_API_BASE_URL` delega a `demoApi.js`;
- con `VITE_API_BASE_URL` effettua richieste HTTP al backend;
- aggiunge automaticamente il JWT salvato alle richieste autenticate;
- converte gli errori HTTP in messaggi visualizzabili dalla UI.

Questo permette di sviluppare l'interfaccia senza infrastruttura e di provare
l'integrazione reale cambiando una sola variabile.

## Funzionalità future

- completare dalla UI l'intero flusso dell'asta live, inclusi rilanci e polling;
- aggiungere creazione/chiusura giornate e inserimento formazione;
- integrare nella dashboard classifica LEC e performance reali PandaScore;
- aggiungere importazione amministrativa dei CSV Oracle's Elixir;
- sostituire gli avatar testuali con immagini ottimizzate dei giocatori;
- aggiungere test end-to-end con Playwright;
- introdurre notifiche in tempo reale tramite WebSocket/SSE;
- internazionalizzare italiano e inglese;
- migliorare la gestione delle sessioni scadute e il refresh dei token;
- aggiungere screenshot automatici e visual regression test.

## Riferimenti utili

- [React: Thinking in React](https://react.dev/learn/thinking-in-react)
- [React: useContext](https://react.dev/reference/react/useContext)
- [React Router tutorial](https://reactrouter.com/en/main/start/tutorial)
- [Material UI customization](https://mui.com/material-ui/customization/how-to-customize/)
- [Vite environment variables](https://vite.dev/guide/env-and-mode)
- [Testing Library guiding principles](https://testing-library.com/docs/guiding-principles/)
- [Web Content Accessibility Guidelines](https://www.w3.org/WAI/standards-guidelines/wcag/)
- [Spring Boot CORS documentation](https://docs.spring.io/spring-framework/reference/web/webmvc-cors.html)

## Note legali

Progetto dimostrativo e didattico. League of Legends, LEC e i relativi marchi
appartengono ai rispettivi proprietari. Il progetto non è affiliato o sponsorizzato da
Riot Games.
