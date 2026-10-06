/* Accesso ai dati per competizione (sostituisce lec-data-source.js, ora parametrico). */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.CompetitionDataSource = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const code = competition => encodeURIComponent(String(competition || 'LEC').toLowerCase());

    function normalizeCumulativeSection(payload) {
        if (Array.isArray(payload)) return {status: 'awaiting-data', lastUpdatedAt: null, provisional: true, items: payload};
        return {
            status: payload?.status || 'awaiting-data',
            lastUpdatedAt: payload?.lastUpdatedAt || null,
            provisional: payload?.provisional ?? true,
            ruleset: payload?.ruleset || 'REGIONAL',
            items: Array.isArray(payload?.items) ? payload.items : []
        };
    }

    function cumulativeFreshnessLabel(section) {
        if (section?.status === 'stale') return `Dati provvisori · ultimo aggiornamento ${section.lastUpdatedAt ? new Date(section.lastUpdatedAt).toLocaleString('it-IT') : 'non disponibile'}`;
        if (section?.status !== 'fresh' || !section.lastUpdatedAt) return 'In attesa della prima sincronizzazione';
        return `Aggiornato ${new Date(section.lastUpdatedAt).toLocaleString('it-IT')}`;
    }

    return {
        normalizeCumulativeSection,
        cumulativeFreshnessLabel,
        loadCompetitions(request) { return request('/competitions'); },
        loadEditions(request, competition) { return request(`/competitions/${code(competition)}/editions`); },
        loadTeams(request, competition, editionId) { return request(editionId ? `/teams?edition=${encodeURIComponent(editionId)}` : `/teams?competition=${code(competition)}`); },
        loadPlayers(request, competition, editionId) { return request(editionId ? `/players?edition=${encodeURIComponent(editionId)}` : `/players?competition=${code(competition)}`); },
        loadStandings(request, competition) { return request(`/competitions/${code(competition)}/standings`); },
        loadPlayerPerformances(request, competition) { return request(`/competitions/${code(competition)}/performances`); },
        async loadCumulativePerformances(request, competition) { return normalizeCumulativeSection(await request(`/competitions/${code(competition)}/cumulative-performances`)); },
        async loadCumulativeRanking(request, leagueId) { return normalizeCumulativeSection(await request(`/leagues/${encodeURIComponent(leagueId)}/cumulative-ranking`)); },
        loadMatches(request, competition) { return request(`/competitions/${code(competition)}/matches`); },
        loadGame(request, competition, matchId, gameId) { return request(`/competitions/${code(competition)}/matches/${encodeURIComponent(matchId)}/games/${encodeURIComponent(gameId)}`); },
        loadFeed(request, competition, state, limit = 50) { return request(`/esports/matches?competition=${code(competition || 'all')}&state=${encodeURIComponent(state)}&limit=${limit}`); },
        loadMatchGames(request, matchId) { return request(`/esports/matches/${encodeURIComponent(matchId)}/games`); },
        loadSynchronization(request, competition) { return request(`/admin/competitions/${code(competition)}/synchronization`); },
        synchronize(request, competition) { return request(`/admin/competitions/${code(competition)}/synchronize`, {method: 'POST'}); },
        correctPlayerGame(request, gameId, playerId, correction) { return request(`/admin/games/${encodeURIComponent(gameId)}/players/${encodeURIComponent(playerId)}`, {method: 'PUT', body: JSON.stringify(correction)}); },
        restorePlayerGame(request, gameId, playerId) { return request(`/admin/games/${encodeURIComponent(gameId)}/players/${encodeURIComponent(playerId)}/override`, {method: 'DELETE'}); }
    };
});
