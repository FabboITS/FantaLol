/* Pagina partite: freschezza dei dati, stati e box score (attribuzione Leaguepedia sempre visibile). */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.MatchesView = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const STATES = ['upcoming', 'results', 'live'];
    const DEFAULT_ATTRIBUTION = 'Statistiche delle partite da Leaguepedia (lol.fandom.com), contenuti disponibili con licenza CC BY-SA 3.0.';

    function freshness(feed, now = Date.now()) {
        if (!feed?.lastSyncedAt) return {label: 'In attesa della prima sincronizzazione', stale: true};
        const minutes = Math.max(0, Math.round((now - Date.parse(feed.lastSyncedAt)) / 60000));
        const age = minutes < 1 ? 'meno di un minuto fa' : minutes === 1 ? '1 minuto fa' : minutes < 120 ? `${minutes} minuti fa` : `${Math.round(minutes / 60)} ore fa`;
        return {label: `${feed.stale ? 'Dati non aggiornati' : 'Aggiornato'} · ${age} · fonte ${feed.source || 'PandaScore'}`, stale: Boolean(feed.stale)};
    }

    function statusLabel(match) {
        return {not_started: 'In programma', running: 'Live', finished: 'Concluso', canceled: 'Annullato', postponed: 'Rinviato'}[match?.status] || 'In attesa';
    }

    function scoreLine(match) {
        const teams = match?.teams || [];
        if (teams.length !== 2) return match?.name || '';
        if (match.status === 'not_started') return `${teams[0].acronym || teams[0].name} vs ${teams[1].acronym || teams[1].name}`;
        return `${teams[0].acronym || teams[0].name} ${teams[0].score} - ${teams[1].score} ${teams[1].acronym || teams[1].name}`;
    }

    function groupPlayersByTeam(players) {
        const groups = new Map();
        for (const player of players || []) {
            const key = player.teamName || 'Team';
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(player);
        }
        return [...groups.entries()].map(([team, list]) => ({team, players: list}));
    }

    function kdaLabel(player) {
        return player.perfectKda ? 'Perfetto' : Number(player.kda ?? 0).toFixed(2);
    }

    function attribution(payload) {
        return payload?.attribution || DEFAULT_ATTRIBUTION;
    }

    return {STATES, DEFAULT_ATTRIBUTION, freshness, statusLabel, scoreLine, groupPlayersByTeam, kdaLabel, attribution};
});
