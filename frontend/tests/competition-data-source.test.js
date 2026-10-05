const test = require('node:test');
const assert = require('node:assert/strict');
const source = require('../js/competition-data-source.js');

function recorder() {
  const calls = [];
  const request = async (path, options) => { calls.push([path, options?.method || 'GET']); return {items: []}; };
  return {calls, request};
}

test('every loader is parametric on the competition code', async () => {
  const {calls, request} = recorder();
  await source.loadStandings(request, 'LCK');
  await source.loadPlayerPerformances(request, 'LPL');
  await source.loadMatches(request, 'WORLDS');
  await source.loadGame(request, 'lec', 7, 'G 1');
  await source.loadPlayers(request, 'LCK');
  await source.loadPlayers(request, 'LCK', 12);
  await source.loadTeams(request, 'LPL');
  await source.loadEditions(request, 'WORLDS');
  assert.deepEqual(calls.map(call => call[0]), [
    '/competitions/lck/standings', '/competitions/lpl/performances', '/competitions/worlds/matches',
    '/competitions/lec/matches/7/games/G%201', '/players?competition=lck', '/players?edition=12',
    '/teams?competition=lpl', '/competitions/worlds/editions'
  ]);
});

test('pipeline feed, box score and admin endpoints', async () => {
  const {calls, request} = recorder();
  await source.loadFeed(request, 'LEC', 'results', 20);
  await source.loadFeed(request, null, 'live');
  await source.loadMatchGames(request, 42);
  await source.loadSynchronization(request, 'LCK');
  await source.synchronize(request, 'LCK');
  await source.correctPlayerGame(request, 'G1', 3, {kills: 1});
  await source.restorePlayerGame(request, 'G1', 3);
  assert.deepEqual(calls, [
    ['/esports/matches?competition=lec&state=results&limit=20', 'GET'],
    ['/esports/matches?competition=all&state=live&limit=50', 'GET'],
    ['/esports/matches/42/games', 'GET'],
    ['/admin/competitions/lck/synchronization', 'GET'],
    ['/admin/competitions/lck/synchronize', 'POST'],
    ['/admin/games/G1/players/3', 'PUT'],
    ['/admin/games/G1/players/3/override', 'DELETE']
  ]);
});

test('cumulative loaders preserve public freshness wrappers', async () => {
  const wrapped = {status: 'stale', lastUpdatedAt: '2026-07-28T12:00:00Z', provisional: true, ruleset: 'WORLDS', items: [{id: 1}]};
  const request = async () => wrapped;
  assert.deepEqual(await source.loadCumulativePerformances(request, 'LEC'), wrapped);
  assert.deepEqual(await source.loadCumulativeRanking(request, 5), wrapped);
  assert.deepEqual(source.normalizeCumulativeSection([{id: 2}]), {status: 'awaiting-data', lastUpdatedAt: null, provisional: true, items: [{id: 2}]});
  assert.match(source.cumulativeFreshnessLabel(wrapped), /^Dati provvisori · ultimo aggiornamento/);
  assert.equal(source.cumulativeFreshnessLabel({status: 'awaiting-data'}), 'In attesa della prima sincronizzazione');
  assert.match(source.cumulativeFreshnessLabel({status: 'fresh', lastUpdatedAt: '2026-07-28T12:00:00Z'}), /^Aggiornato /);
});
