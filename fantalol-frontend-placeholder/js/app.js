/* Client minimale delle API FantaLoL: serve solo alla verifica manuale.
   Tutti i dati arrivano dal backend Django: nessuna chiamata diretta a
   PandaScore o Leaguepedia, esattamente come nel frontend definitivo. */
(function () {
  "use strict";

  const TOKEN_KEY = "fantalol.placeholder.token";

  const $ = (id) => document.getElementById(id);
  const val = (id) => ($(id) ? $(id).value.trim() : "");
  const idList = (id) => val(id).split(",").map((s) => s.trim()).filter(Boolean).map(Number);

  /* Quando la pagina è servita da Django (stessa origine) l'API sta su /api;
     aperta da file:// si ripiega sul backend locale. */
  function defaultApiBase() {
    return location.protocol.startsWith("http")
      ? location.origin + "/api"
      : "http://localhost:8080/api";
  }

  function apiBase() {
    return (val("api-base") || defaultApiBase()).replace(/\/$/, "");
  }

  function token() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function show(payload, isError) {
    const output = $("output");
    if (output) {
      output.textContent = typeof payload === "string"
        ? payload
        : JSON.stringify(payload, null, 2);
      output.style.color = isError ? "#ff7b72" : "";
    }
    const attribution = $("attribution");
    if (attribution) {
      attribution.textContent = (payload && payload.attribution) || "";
    }
  }

  function setAuthState(text, cls) {
    const state = $("auth-state");
    if (state) {
      state.textContent = text;
      state.className = "state " + (cls || "");
    }
  }

  async function call(path, options) {
    const opts = options || {};
    const headers = { Accept: "application/json" };
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (token()) headers.Authorization = "Bearer " + token();

    const response = await fetch(apiBase() + path, {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    });

    const text = await response.text();
    let payload = text;
    try { payload = text ? JSON.parse(text) : null; } catch (_) { /* testo grezzo */ }
    if (!response.ok) {
      const message = (payload && payload.message) || response.statusText;
      show({ status: response.status, message: message, body: payload }, true);
      throw new Error(message);
    }
    show(payload, false);
    return payload;
  }

  window.fantalol = { call: call, show: show, apiBase: apiBase, token: token, $: $ };

  const actions = {
    async register() {
      const data = await call("/auth/register", {
        method: "POST",
        body: { username: val("username"), email: val("email"), password: val("password") },
      });
      localStorage.setItem(TOKEN_KEY, data.token);
      setAuthState("Registrato come " + data.username + " (" + data.role + ")", "ok");
    },
    async login() {
      const data = await call("/auth/login", {
        method: "POST",
        body: { username: val("username"), password: val("password") },
      });
      localStorage.setItem(TOKEN_KEY, data.token);
      setAuthState("Autenticato come " + data.username + " (" + data.role + ")", "ok");
    },
    async me() {
      const data = await call("/users/me");
      setAuthState("Sessione valida: " + data.username, "ok");
    },
    logout() {
      localStorage.removeItem(TOKEN_KEY);
      setAuthState("Non autenticato", "");
      show("Token rimosso.");
    },

    createLeague: () => call("/leagues", {
      method: "POST",
      body: {
        nome: val("league-name"),
        creditiIniziali: Number(val("league-credits")) || undefined,
        competition: val("league-competition"),
      },
    }),
    listLeagues: () => call("/leagues"),
    joinLeague: () => call("/fanta-teams/join", {
      method: "POST",
      body: { codiceInvito: val("invite-code"), nomeSquadra: val("team-name") },
    }),
    myTeams: () => call("/fanta-teams/me"),
    openAuction: () => call("/leagues/" + val("league-id") + "/auction/open", { method: "PUT" }),
    closeAuction: () => call("/leagues/" + val("league-id") + "/auction/close", { method: "PUT" }),
    ranking: () => call("/leagues/" + val("league-id") + "/cumulative-ranking"),

    listPlayers: () => call("/players?competition=" + val("players-competition")),
    cumulative: () => call("/lec/cumulative-performances?competition=" + val("players-competition")),
    lineupWindow: () => call("/fanta-teams/" + val("fanta-team-id") + "/formazioni/window"),
    lineup: () => call("/fanta-teams/" + val("fanta-team-id") + "/formazioni/lineup"),
    saveLineup: () => call("/fanta-teams/" + val("fanta-team-id") + "/formazioni/lineup", {
      method: "PUT",
      body: { titolariIds: idList("lineup-ids") },
    }),

    worldsEditions: () => call("/worlds/editions/"),
    worldsStages: () => call("/worlds/editions/" + val("worlds-edition-id") + "/stages/"),
    worldsPool: () => call("/worlds/editions/" + val("worlds-edition-id") + "/pool/"),
    worldsCreateLeague: () => call("/worlds/leagues/", {
      method: "POST",
      body: { nome: val("worlds-league-name"), editionId: Number(val("worlds-edition-id")) },
    }),
    worldsLeagues: () => call("/worlds/leagues/"),
    worldsLineup: () => call("/worlds/leagues/" + val("worlds-league-id") + "/lineup/", {
      method: "POST",
      body: {
        fantaTeamId: Number(val("worlds-team-id")),
        titolariIds: idList("worlds-lineup-ids"),
      },
    }),
    worldsStandings: () => call("/worlds/leagues/" + val("worlds-league-id") + "/standings/"),

    ingestStatus: () => call("/admin/ingest/status"),
    syncPandascore: () => call("/admin/ingest/pandascore/sync", { method: "POST" }),
    syncLeaguepedia: () => call("/admin/ingest/leaguepedia/sync", { method: "POST" }),
    matches: () => call("/matches"),
  };

  // "create-league" -> createLeague
  function toCamel(name) {
    return name.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
  }

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const handler = actions[toCamel(button.dataset.action)];
    if (!handler) return;  // gestito da un altro script (es. league-detail.js)
    event.preventDefault();
    Promise.resolve()
      .then(handler)
      .catch((error) => console.warn("Chiamata fallita:", error.message));
  });

  const apiBaseInput = $("api-base");
  if (apiBaseInput && !apiBaseInput.value.trim()) apiBaseInput.value = defaultApiBase();

  if (token()) setAuthState("Token presente in localStorage", "ok");
})();
