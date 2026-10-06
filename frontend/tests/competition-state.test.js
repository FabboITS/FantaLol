const test = require('node:test');
const assert = require('node:assert/strict');
const CompetitionState = require('../js/competition-state.js');

function memoryStorage(initial = {}) {
  const data = {...initial};
  return {getItem: key => data[key] ?? null, setItem: (key, value) => { data[key] = value; }, data};
}

test('the selected competition is persisted in localStorage and defaults to LEC', () => {
  const storage = memoryStorage();
  assert.equal(CompetitionState.read(storage), 'LEC');
  assert.equal(CompetitionState.write(storage, 'lpl'), 'LPL');
  assert.equal(storage.data.fantalol_competition, 'LPL');
  assert.equal(CompetitionState.read(storage), 'LPL');
  assert.equal(CompetitionState.read(memoryStorage({fantalol_competition: 'LCS'})), 'LEC');
});

test('storage failures never break the page', () => {
  const broken = {getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); }};
  assert.equal(CompetitionState.read(broken), 'LEC');
  assert.equal(CompetitionState.write(broken, 'WORLDS'), 'WORLDS');
});

test('chips render the four competitions with the active one pressed', () => {
  const html = CompetitionState.chipsHtml('LCK');
  for (const code of ['LEC', 'LCK', 'LPL', 'WORLDS']) assert.match(html, new RegExp(`data-competition="${code}"`));
  assert.match(html, /class="competition-chip active" data-competition="LCK" aria-pressed="true"/);
  assert.match(CompetitionState.chipsHtml('WORLDS', 'data-league-competition'), /data-league-competition="WORLDS"/);
  assert.ok(CompetitionState.isWorlds('worlds'));
  assert.equal(CompetitionState.find('lpl').name, 'LoL Pro League');
});
