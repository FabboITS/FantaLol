/* Sezione Players: raggruppamento per team, filtri e fallback grafico delle immagini. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.PlayersView = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const ROLE_ORDER = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
    const PALETTE = ['#4f8cff', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

    function initials(name) {
        const words = String(name || '?').replace(/[^\p{L}\p{N} ]/gu, ' ').trim().split(/\s+/).filter(Boolean);
        if (!words.length) return '?';
        if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
        return (words[0][0] + words[1][0]).toUpperCase();
    }

    function avatarColor(name) {
        let hash = 0;
        for (const char of String(name || '')) hash = (hash * 31 + char.codePointAt(0)) >>> 0;
        return PALETTE[hash % PALETTE.length];
    }

    function matches(player, filters) {
        const role = (filters?.role || '').toUpperCase();
        const query = (filters?.query || '').trim().toLowerCase();
        if (role && player.ruolo !== role) return false;
        if (!query) return true;
        return [player.nickname, player.teamNome, player.teamSigla, player.nazionalita]
            .some(value => String(value || '').toLowerCase().includes(query));
    }

    function filterPlayers(players, filters) {
        return (players || []).filter(player => matches(player, filters));
    }

    function sortByRole(players) {
        return [...(players || [])].sort((left, right) =>
            ROLE_ORDER.indexOf(left.ruolo) - ROLE_ORDER.indexOf(right.ruolo)
            || String(left.nickname).localeCompare(String(right.nickname), 'it'));
    }

    /** Team (logo, nome, sigla) → player ordinati per ruolo; i team senza player filtrati spariscono. */
    function groupByTeam(teams, players, filters) {
        const visible = filterPlayers(players, filters);
        const byTeam = new Map();
        for (const player of visible) {
            const key = Number(player.teamId);
            if (!byTeam.has(key)) byTeam.set(key, []);
            byTeam.get(key).push(player);
        }
        const known = new Map((teams || []).map(team => [Number(team.id), team]));
        const groups = [];
        for (const [teamId, teamPlayers] of byTeam) {
            const team = known.get(teamId) || {id: teamId, nome: teamPlayers[0].teamNome, sigla: teamPlayers[0].teamSigla, logoUrl: teamPlayers[0].teamLogoUrl};
            groups.push({team, players: sortByRole(teamPlayers)});
        }
        return groups.sort((left, right) => String(left.team.nome).localeCompare(String(right.team.nome), 'it'));
    }

    return {ROLE_ORDER, initials, avatarColor, filterPlayers, sortByRole, groupByTeam};
});
