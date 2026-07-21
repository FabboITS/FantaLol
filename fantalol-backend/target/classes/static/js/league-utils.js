(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.LeagueUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    function parseLeagueId(search) {
        const raw = new URLSearchParams(search).get('id');
        if (!raw || !/^\d+$/.test(raw)) return null;
        const id = Number(raw);
        return Number.isSafeInteger(id) && id > 0 ? id : null;
    }

    function rankFantasyTeams(teams) {
        return teams
            .map(team => ({...team, punti: Number.isFinite(Number(team.punti)) ? Number(team.punti) : 0}))
            .sort((left, right) => right.punti - left.punti || left.nome.localeCompare(right.nome, 'it'));
    }

    return {parseLeagueId, rankFantasyTeams};
});
