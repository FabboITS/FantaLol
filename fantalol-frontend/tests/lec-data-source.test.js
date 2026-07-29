const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../js/lec-data-source.js'), 'utf8');
const browser = {window: {}};
vm.runInNewContext(source, browser);
const dataSource = browser.window.LecDataSource;

test('LEC data source loads every normalized backend projection', () => {
  assert.match(source, /\/lec\/standings/);
  assert.match(source, /\/lec\/performances/);
  assert.match(source, /\/lec\/matches/);
  assert.match(source, /loadGame/);
  assert.doesNotMatch(source, /not-connected/);
});

test('LEC data source loads cumulative projections and ADMIN synchronization endpoints', () => {
  assert.match(source, /\/lec\/cumulative-performances/);
  assert.match(source, /\/leagues\/\$\{encodeURIComponent\(leagueId\)\}\/cumulative-ranking/);
  assert.match(source, /\/admin\/lec\/synchronization/);
  assert.match(source, /\/admin\/lec\/synchronize/);
});

test('cumulative loaders preserve public freshness wrappers', async () => {
  const wrapped = {
    status: 'stale',
    lastUpdatedAt: '2026-07-28T12:00:00Z',
    provisional: true,
    items: [{nickname: 'Caps'}]
  };

  const result = await dataSource.loadCumulativePerformances(async path => {
    assert.equal(path, '/lec/cumulative-performances');
    return wrapped;
  });

  assert.equal(result.status, 'stale');
  assert.equal(result.lastUpdatedAt, '2026-07-28T12:00:00Z');
  assert.equal(result.provisional, true);
  assert.deepEqual(Array.from(result.items), [{nickname: 'Caps'}]);
});

test('cumulative loaders keep legacy arrays visible with awaiting freshness', async () => {
  const result = await dataSource.loadCumulativeRanking(
    async path => {
      assert.equal(path, '/leagues/7/cumulative-ranking');
      return [{fantasyTeamId: 3, provisional: false}];
    },
    7
  );

  assert.equal(result.status, 'awaiting-data');
  assert.equal(result.lastUpdatedAt, null);
  assert.equal(result.provisional, true);
  assert.deepEqual(Array.from(result.items), [{fantasyTeamId: 3, provisional: false}]);
});

test('cumulative freshness labels distinguish source state from item state', () => {
  assert.equal(
    dataSource.cumulativeFreshnessLabel({status: 'awaiting-data', lastUpdatedAt: null}),
    'In attesa della prima sincronizzazione'
  );
  assert.match(
    dataSource.cumulativeFreshnessLabel({status: 'stale', lastUpdatedAt: '2026-07-28T12:00:00Z'}),
    /^Dati provvisori · ultimo aggiornamento /i
  );
  assert.match(
    dataSource.cumulativeFreshnessLabel({status: 'fresh', lastUpdatedAt: '2026-07-28T14:00:00Z'}),
    /^Aggiornato /i
  );
});
