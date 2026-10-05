# Changelog

## 2.0.0 — FantaLol multi-competizione

### Aggiunto
- Backend riscritto in Python 3.12 / Django 5.2 / Django REST Framework / PostgreSQL 16
  (`backend/`), con gli stessi path, nomi dei campi JSON e codici di stato del backend Java.
- Quattro competizioni: LEC, LCK, LPL (regolamento regionale generalizzato) e WORLDS (nuovo
  regolamento a listone in stile FantaChampions, `Rules-WORLDS.md`).
- Edizioni configurabili (`CompetitionEdition`), fasi Worlds (`Stage`) e politiche di formazione per
  edizione (`LineupPolicy`: finestra settimanale LEC, blocco 60 minuti prima della prima serie per
  LCK/LPL/WORLDS).
- Pipeline dati PandaScore (calendario, risultati, roster) + Leaguepedia (statistiche per game) con
  scheduler dedicato, alias, correzioni manuali e attribuzione CC BY-SA (`docs/pro-matches-pipeline.md`).
- Endpoint `/api/competitions/**`, `/api/esports/matches`, `/api/worlds/**` e amministrazione dei dati
  reali; alias compatibili `/api/lec/**` e `/api/admin/lec/**`.
- Immagini locali di team e player (`download_esports_images`, `import_legacy_assets`) e migrazione
  dei dati dal MySQL del backend Java (`migrate_from_mysql`).
- Frontend `frontend/` (ex `fantalol-frontend/`): selettore di competizione, sezione Players per team,
  match center con box score, creazione lega con edizione, sezioni WORLDS (listone, cambi, capitano).

### Rimosso
- Integrazione **Oracle's Elixir**: client e importer CSV, controller di import
  (`/api/admin/oracle-elixir/...`), proprietà `oracle-csv-url`, workflow `update-lec-csv.yml` con i
  segreti `ORACLE_FILE_ID`/`R2_*`, file `lec-summer-2026-filtered.csv` e fixture di test
  `oracle-elixir-sample.csv`. Le statistiche per game arrivano ora da Leaguepedia.
- Backend Java / Spring Boot (`fantalol-backend/`, incluse le build `target/` versionate) e i
  documenti di pianificazione relativi (`docs/superpowers/`).
