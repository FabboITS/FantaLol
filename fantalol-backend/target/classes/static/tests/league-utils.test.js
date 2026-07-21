const test = require('node:test');
const assert = require('node:assert/strict');
const { parseLeagueId, rankFantasyTeams } = require('../js/league-utils.js');

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
