const test = require('node:test');
const assert = require('node:assert/strict');
const {
  parseLeagueId,
  rankFantasyTeams,
  auctionViewState,
  remainingAuctionSeconds,
  mergeBidDraft,
  participantCreditBalances
} = require('../js/league-utils.js');

test('parseLeagueId accepts a positive integer id', () => {
  assert.equal(parseLeagueId('?id=12'), 12);
});

test('parseLeagueId rejects missing, zero, negative, and non-numeric ids', () => {
  for (const search of ['', '?id=0', '?id=-2', '?id=abc', '?id=1.5']) {
    assert.equal(parseLeagueId(search), null);
  }
});

test('rankFantasyTeams sorts alphabetically and supplies zero points when scores are unavailable', () => {
  const input = [{ nome: 'Zeta' }, { nome: 'Alpha' }, { nome: 'Beta' }];
  assert.deepEqual(
    rankFantasyTeams(input).map(team => [team.nome, team.punti]),
    [['Alpha', 0], ['Beta', 0], ['Zeta', 0]]
  );
  assert.equal(input[0].punti, undefined);
});

test('rankFantasyTeams sorts real scores descending and names alphabetically on ties', () => {
  const input = [
    { nome: 'Zeta', punti: 8 },
    { nome: 'Beta', punti: 12 },
    { nome: 'Alpha', punti: 12 }
  ];
  assert.deepEqual(
    rankFantasyTeams(input).map(team => team.nome),
    ['Alpha', 'Beta', 'Zeta']
  );
});

test('auctionViewState prevents the current leader from bidding', () => {
  const auction = { currentBid: 120, highestBidderId: 7 };
  const team = { id: 7, creditiResidui: 500 };

  assert.deepEqual(auctionViewState(auction, team, 150), {
    nextMinimum: 121,
    canAfford: true,
    isCurrentLeader: true,
    canBid: false,
    draftAmount: 150
  });
});

test('auctionViewState allows a challenger to submit a custom valid bid', () => {
  const auction = { currentBid: 120, highestBidderId: 8 };
  const team = { id: 7, creditiResidui: 500 };

  assert.equal(auctionViewState(auction, team, 275).canBid, true);
});

test('remainingAuctionSeconds derives a non-negative value from the server deadline', () => {
  assert.equal(remainingAuctionSeconds('2026-07-23T12:00:15Z', Date.parse('2026-07-23T12:00:04Z')), 11);
  assert.equal(remainingAuctionSeconds('2026-07-23T12:00:00Z', Date.parse('2026-07-23T12:00:04Z')), 0);
});

test('mergeBidDraft preserves valid custom input and raises an obsolete draft to the new minimum', () => {
  const team = { id: 7, creditiResidui: 500 };

  assert.equal(mergeBidDraft(275, { currentBid: 120, highestBidderId: 8 }, team), 275);
  assert.equal(mergeBidDraft(121, { currentBid: 150, highestBidderId: 8 }, team), 151);
});

test('participantCreditBalances projects only the current leader balance', () => {
  const teams = [
    { id: 7, nome: 'Alpha', creditiResidui: 500 },
    { id: 8, nome: 'Beta', creditiResidui: 420 }
  ];

  assert.deepEqual(
    participantCreditBalances(teams, { highestBidderId: '8', currentBid: 120 })
      .map(team => [team.nome, team.displayCredits, team.isProjected]),
    [['Alpha', 500, false], ['Beta', 300, true]]
  );
});

test('participantCreditBalances uses safe persisted balances without an auction', () => {
  const teams = [
    { id: 7, nome: 'Alpha', creditiResidui: '500' },
    { id: 8, nome: 'Beta', creditiResidui: null }
  ];

  assert.deepEqual(
    participantCreditBalances(teams, null).map(team => team.displayCredits),
    [500, 0]
  );
});

test('participantCreditBalances clamps a projected balance to zero', () => {
  const [leader] = participantCreditBalances(
    [{ id: 7, nome: 'Alpha', creditiResidui: 50 }],
    { highestBidderId: 7, currentBid: 80 }
  );

  assert.equal(leader.displayCredits, 0);
  assert.equal(leader.isProjected, true);
});
