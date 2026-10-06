# ADR 0001 — WORLDS senza esclusività (listone stile FantaChampions)

* **Stato:** Proposta (default applicato)
* **Contesto:** nel regionale ogni pro appartiene a un solo FantaTeam della lega (asta esclusiva). Ai
  Worlds partecipano 16 squadre utili (80 titolari) e le leghe possono avere fino a 50 partecipanti:
  un'asta esclusiva lascerebbe rose incomplete o di qualità molto diversa.
* **Decisione:** listone a prezzi fissi come FantaChampions / Fantasy UCL. Ogni partecipante compra
  liberamente con un budget; lo stesso player può essere in più FantaTeam. Nessuna asta.
  Implementazione: `RosterEntry.exclusive=False` per le leghe WORLDS (il vincolo univoco
  `uniq_exclusive_player_league` è condizionale), mercato in `apps/worlds/services.py`.
* **Variante futura:** flag `League.settings.worlds_exclusive` (oggi `false`; il valore `true` è
  rifiutato con un messaggio esplicito finché la variante non sarà implementata).
* **Conseguenze:** la competizione si gioca su scelte di capitano, panchina e tempismo dei cambi più
  che sull'esclusiva dei top player.
