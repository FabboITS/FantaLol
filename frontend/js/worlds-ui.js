/* Regolamento WORLDS lato interfaccia: contatori per team, cambi residui, validazione formazione. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.WorldsUi = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const ROLES = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
    const RULES_SUMMARY = [
        'Rosa da 8 player: 5 titolari (uno per ruolo) + 3 panchinari ordinati',
        'Budget 100 crediti, +5 dopo lo Swiss Stage; listone a prezzi fissi (5–20)',
        'Nessuna esclusività: lo stesso player può stare in più squadre',
        'Massimo 2 player dello stesso team nello Swiss, 3 nei quarti, 4 in semifinale, 5 in finale',
        'Cambi illimitati prima di G1 e a ogni passaggio di fase; nello Swiss 2 gratuiti per giornata, poi −3 punti',
        'Capitano ×2 (vice se il capitano non gioca), sostituzioni automatiche solo pari ruolo'
    ];

    function teamCounters(roster, limit) {
        const counts = new Map();
        for (const entry of roster || []) {
            const key = entry.teamNome || entry.teamId || 'Team';
            counts.set(key, (counts.get(key) || 0) + 1);
        }
        return [...counts.entries()].map(([team, count]) => ({team, count, limit: limit ?? null, over: limit != null && count > limit}))
            .sort((left, right) => right.count - left.count || String(left.team).localeCompare(String(right.team), 'it'));
    }

    function transfersLabel(summary) {
        if (!summary) return 'Mercato non disponibile';
        if (summary.unlimited) return 'Cambi illimitati e gratuiti per la prossima giornata';
        const remaining = summary.freeTransfersRemaining ?? 0;
        return `${remaining} ${remaining === 1 ? 'cambio gratuito' : 'cambi gratuiti'} rimasti · ogni cambio extra costa ${summary.extraTransferPenalty ?? 3} punti`;
    }

    function validateLineup({starters, bench, captainId, viceId, rolesById}) {
        const errors = [];
        const ids = (starters || []).map(Number).filter(Boolean);
        if (ids.length !== 5 || new Set(ids).size !== 5) errors.push('Scegli 5 titolari diversi');
        const roles = ids.map(id => rolesById?.[id]).sort();
        if (roles.join() !== [...ROLES].sort().join()) errors.push('Serve un titolare per ruolo');
        const benchIds = (bench || []).map(Number).filter(Boolean);
        if (benchIds.some(id => ids.includes(id)) || new Set(benchIds).size !== benchIds.length) errors.push('La panchina non può contenere titolari o doppioni');
        if (!ids.includes(Number(captainId)) || !ids.includes(Number(viceId)) || Number(captainId) === Number(viceId)) errors.push('Capitano e vice devono essere due titolari diversi');
        return errors;
    }

    function marketRows(items, filters) {
        const role = (filters?.role || '').toUpperCase();
        const team = filters?.team ? Number(filters.team) : null;
        return (items || []).filter(item => (!role || item.ruolo === role) && (!team || Number(item.teamId) === team));
    }

    return {ROLES, RULES_SUMMARY, teamCounters, transfersLabel, validateLineup, marketRows};
});
