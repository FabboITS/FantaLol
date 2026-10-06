const test = require('node:test');
const assert = require('node:assert/strict');
const MatchesView = require('../js/matches-view.js');

test('freshness label reflects lastSyncedAt and the stale flag', () => {
  const now = Date.parse('2026-10-05T12:00:00Z');
  assert.equal(MatchesView.freshness(null).stale, true);
  assert.match(MatchesView.freshness({lastSyncedAt: '2026-10-05T11:30:00Z', stale: false, source: 'PandaScore'}, now).label, /^Aggiornato · 30 minuti fa · fonte PandaScore$/);
  const stale = MatchesView.freshness({lastSyncedAt: '2026-10-05T08:00:00Z', stale: true}, now);
  assert.equal(stale.stale, true);
  assert.match(stale.label, /Dati non aggiornati · 4 ore fa/);
});

test('score line, status labels and KDA', () => {
  const match = {status: 'finished', teams: [{acronym: 'GEN', score: 2}, {acronym: 'T1', score: 1}]};
  assert.equal(MatchesView.scoreLine(match), 'GEN 2 - 1 T1');
  assert.equal(MatchesView.scoreLine({...match, status: 'not_started'}), 'GEN vs T1');
  assert.equal(MatchesView.statusLabel({status: 'postponed'}), 'Rinviato');
  assert.equal(MatchesView.kdaLabel({perfectKda: true}), 'Perfetto');
  assert.equal(MatchesView.kdaLabel({perfectKda: false, kda: 3.456}), '3.46');
});

test('box score groups players by team and always carries the CC BY-SA attribution', () => {
  const groups = MatchesView.groupPlayersByTeam([{teamName: 'Gen.G', nickname: 'Chovy'}, {teamName: 'T1', nickname: 'Faker'}, {teamName: 'Gen.G', nickname: 'Ruler'}]);
  assert.deepEqual(groups.map(group => [group.team, group.players.length]), [['Gen.G', 2], ['T1', 1]]);
  assert.match(MatchesView.attribution({}), /CC BY-SA/);
  assert.equal(MatchesView.attribution({attribution: 'X CC BY-SA'}), 'X CC BY-SA');
});
