/* Dettaglio lega: legge ?leagueId= (stagionale) o ?worldsLeagueId= (Worlds). */
(function () {
  "use strict";

  const { call, $ } = window.fantalol;
  const params = new URLSearchParams(location.search);
  const leagueId = params.get("leagueId");
  const worldsLeagueId = params.get("worldsLeagueId");

  function renderTable(container, rows, columns) {
    const target = $(container);
    if (!target) return;
    if (!rows || !rows.length) {
      target.innerHTML = "<p class='state'>Nessun dato.</p>";
      return;
    }
    const head = columns.map((c) => "<th>" + c.label + "</th>").join("");
    const body = rows.map((row) =>
      "<tr>" + columns.map((c) => "<td>" + format(c.get(row)) + "</td>").join("") + "</tr>"
    ).join("");
    target.innerHTML = "<table><thead><tr>" + head + "</tr></thead><tbody>" + body + "</tbody></table>";
  }

  function format(value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "number") return Math.round(value * 100) / 100;
    return String(value);
  }

  const handlers = {
    "detail-teams": async function () {
      if (worldsLeagueId) {
        const teams = await call("/worlds/leagues/" + worldsLeagueId + "/teams/");
        renderTable("teams", teams, [
          { label: "Squadra", get: (t) => t.nome },
          { label: "Proprietario", get: (t) => t.ownerUsername },
          { label: "Crediti", get: (t) => t.creditiResidui },
          { label: "Rosa", get: (t) => t.rosa.filter((r) => !r.released).length },
        ]);
        return;
      }
      const teams = await call("/fanta-teams/by-league/" + leagueId);
      renderTable("teams", teams, [
        { label: "Squadra", get: (t) => t.nome },
        { label: "Proprietario", get: (t) => t.ownerUsername },
        { label: "Crediti", get: (t) => t.creditiResidui },
        { label: "Rosa", get: (t) => t.rosa.length },
      ]);
    },

    "detail-ranking": async function () {
      if (worldsLeagueId) {
        const payload = await call("/worlds/leagues/" + worldsLeagueId + "/standings/");
        renderTable("ranking", payload.items, [
          { label: "#", get: (r) => r.posizione },
          { label: "Squadra", get: (r) => r.teamNome },
          { label: "Totale", get: (r) => r.totale },
          { label: "Bonus", get: (r) => r.bonusTotale },
        ]);
        return;
      }
      const payload = await call("/leagues/" + leagueId + "/cumulative-ranking");
      renderTable("ranking", payload.items, [
        { label: "Squadra", get: (r) => r.teamName },
        { label: "Totale", get: (r) => r.overallTotal },
        { label: "Provvisorio", get: (r) => (r.provisional ? "sì" : "no") },
      ]);
    },

    "detail-auction": async function () {
      const path = worldsLeagueId
        ? "/worlds/leagues/" + worldsLeagueId + "/auction/"
        : "/auctions/active?leagueId=" + leagueId;
      const auction = await call(path);
      const target = $("auction");
      if (!target) return;
      target.innerHTML = auction
        ? "<p>" + auction.playerNickname + " (" + auction.playerRole + ") — " +
          auction.currentBid + " crediti, miglior offerta: " +
          (auction.highestBidderName || "nessuna") + "</p>"
        : "<p class='state'>Nessuna asta attiva.</p>";
    },
  };

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-action]");
    if (!button || !handlers[button.dataset.action]) return;
    event.preventDefault();
    handlers[button.dataset.action]().catch((error) =>
      console.warn("Chiamata fallita:", error.message));
  });
})();
