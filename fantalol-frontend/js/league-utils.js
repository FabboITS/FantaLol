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

    function rankCumulativeTeams(teams) {
        return [...(teams || [])];
    }

    function lineupWindowState(selectedFormation, formationHistory) {
        const response = selectedFormation || (formationHistory || [])
            .find(formation => typeof formation?.editable === 'boolean');
        return {
            editable: Boolean(response?.editable),
            nextEffectiveAt: response?.nextEffectiveAt || null
        };
    }

    function auctionViewState(auction, activeTeam, draftAmount) {
        const nextMinimum = Number(auction?.currentBid ?? 0) + 1;
        const credits = Number(activeTeam?.creditiResidui ?? 0);
        const normalizedDraft = Number(draftAmount);
        const isCurrentLeader = Boolean(
            auction && activeTeam && Number(auction.highestBidderId) === Number(activeTeam.id)
        );
        const canAfford = credits >= nextMinimum;
        const validDraft = Number.isInteger(normalizedDraft)
            && normalizedDraft >= nextMinimum
            && normalizedDraft <= credits;
        return {
            nextMinimum,
            canAfford,
            isCurrentLeader,
            canBid: Boolean(auction && activeTeam && !isCurrentLeader && canAfford && validDraft),
            draftAmount: normalizedDraft
        };
    }

    function remainingAuctionSeconds(endsAt, now = Date.now()) {
        const deadline = Date.parse(endsAt);
        if (!Number.isFinite(deadline)) return 0;
        return Math.max(0, (deadline - now) / 1000);
    }

    function mergeBidDraft(previousDraft, auction, activeTeam) {
        if (!auction || !activeTeam) return null;
        const nextMinimum = Number(auction.currentBid) + 1;
        const draft = Number(previousDraft);
        if (Number.isInteger(draft) && draft >= nextMinimum) return draft;
        return nextMinimum;
    }

    function participantCreditBalances(teams, auction) {
        return (teams || []).map(team => {
            const remainingCredits = Number.isFinite(Number(team.creditiResidui))
                ? Number(team.creditiResidui)
                : 0;
            const isProjected = Boolean(
                auction && Number(team.id) === Number(auction.highestBidderId)
            );
            const currentBid = Number.isFinite(Number(auction?.currentBid))
                ? Number(auction.currentBid)
                : 0;
            return {
                ...team,
                displayCredits: Math.max(0, remainingCredits - (isProjected ? currentBid : 0)),
                isProjected
            };
        });
    }

    return {
        parseLeagueId,
        rankFantasyTeams,
        rankCumulativeTeams,
        lineupWindowState,
        auctionViewState,
        remainingAuctionSeconds,
        mergeBidDraft,
        participantCreditBalances
    };
});
