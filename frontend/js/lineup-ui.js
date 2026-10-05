(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.LineupUi = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const roleOrder = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

    function sortPlayers(players) {
        return [...(players || [])].sort(
            (left, right) => roleOrder.indexOf(left.role) - roleOrder.indexOf(right.role)
        );
    }

    function sameSelection(left, right) {
        if (left.length !== right.length) return false;
        const effectiveIds = new Set(right.map(player => Number(player.id)));
        return left.every(player => effectiveIds.has(Number(player.id)));
    }

    async function saveLineup(api, fantaTeamId, titolariIds) {
        return api(`/fanta-teams/${fantaTeamId}/formazioni/lineup`, {
            method: 'PUT',
            body: JSON.stringify({titolariIds})
        });
    }

    function lineupViewModel(response) {
        const selectedPlayers = sortPlayers(response?.players);
        const activePlayers = sortPlayers(response?.effectivePlayers);
        const hasPendingSelection = !sameSelection(selectedPlayers, activePlayers);
        return {
            activePlayers,
            pendingPlayers: hasPendingSelection ? selectedPlayers : [],
            pendingEffectiveAt: hasPendingSelection ? response?.nextEffectiveAt || null : null
        };
    }

    return {
        saveLineup,
        lineupViewModel
    };
});
