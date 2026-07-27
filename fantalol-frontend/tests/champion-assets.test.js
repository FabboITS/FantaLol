const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const directory = path.join(__dirname, '../Player_immage/Champions');
const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8'));

test('every Riot champion in the local manifest has a square image', () => {
  const champions = Object.values(manifest.data);
  assert.ok(champions.length > 150);
  for (const champion of champions) {
    assert.ok(fs.existsSync(path.join(directory, `${champion.id}.png`)), champion.id);
  }
  assert.ok(fs.existsSync(path.join(directory, 'unknown.svg')));
});
