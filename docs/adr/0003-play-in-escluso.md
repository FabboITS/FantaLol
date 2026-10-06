# ADR 0003 — Play-In escluso dal punteggio

* **Stato:** Proposta (default applicato)
* **Decisione:** il Play-In (4 squadre) non genera giornate: serve solo a definire il listone, come i
  preliminari di Champions. G1–G5 = Swiss Round 1–5, G6 = quarti, G7 = semifinali, G8 = finale
  (`apps/worlds/services.matchday_plan`).
* **Listone:** prima della pubblicazione si compra solo dalle squadre qualificate direttamente (team
  senza match di Play-In); `POST /api/admin/worlds/editions/{id}/publish-listone` pubblica i player
  delle 16 squadre dello Swiss Stage. I player di squadre non qualificate risultano "eliminati" e
  venderli è gratuito.
