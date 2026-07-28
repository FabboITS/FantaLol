const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../js/lec-data-source.js'), 'utf8');

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
