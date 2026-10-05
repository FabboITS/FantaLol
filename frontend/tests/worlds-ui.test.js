const test = require('node:test');
const assert = require('node:assert/strict');
const WorldsUi = require('../js/worlds-ui.js');

test('per-team counters flag teams over the phase limit', () => {
  const roster = [{teamNome: 'T1'}, {teamNome: 'T1'}, {teamNome: 'T1'}, {teamNome: 'GEN'}];
  assert.deepEqual(WorldsUi.teamCounters(roster, 2), [
    {team: 'T1', count: 3, limit: 2, over: true},
    {team: 'GEN', count: 1, limit: 2, over: false}
  ]);
  assert.equal(WorldsUi.teamCounters([], 3).length, 0);
});

test('transfer status explains free transfers and penalties', () => {
  assert.equal(WorldsUi.transfersLabel({unlimited: true}), 'Cambi illimitati e gratuiti per la prossima giornata');
  assert.equal(WorldsUi.transfersLabel({unlimited: false, freeTransfersRemaining: 1, extraTransferPenalty: 3}), '1 cambio gratuito rimasti · ogni cambio extra costa 3 punti');
  assert.match(WorldsUi.transfersLabel({unlimited: false, freeTransfersRemaining: 0}), /^0 cambi gratuiti/);
  assert.equal(WorldsUi.transfersLabel(null), 'Mercato non disponibile');
});

test('lineup validation: one starter per role, bench without starters, captain and vice among starters', () => {
  const rolesById = {1: 'TOP', 2: 'JUNGLE', 3: 'MID', 4: 'ADC', 5: 'SUPPORT', 6: 'MID'};
  assert.deepEqual(WorldsUi.validateLineup({starters: [1, 2, 3, 4, 5], bench: [6], captainId: 3, viceId: 1, rolesById}), []);
  assert.ok(WorldsUi.validateLineup({starters: [1, 2, 6, 3, 5], bench: [], captainId: 3, viceId: 1, rolesById}).includes('Serve un titolare per ruolo'));
  assert.ok(WorldsUi.validateLineup({starters: [1, 2, 3, 4, 5], bench: [5], captainId: 3, viceId: 3, rolesById}).length === 2);
});

test('market rows filter by role and real team; the rules summary is complete', () => {
  const items = [{ruolo: 'MID', teamId: 1}, {ruolo: 'TOP', teamId: 2}, {ruolo: 'MID', teamId: 2}];
  assert.equal(WorldsUi.marketRows(items, {role: 'mid'}).length, 2);
  assert.equal(WorldsUi.marketRows(items, {role: 'MID', team: '2'}).length, 1);
  assert.equal(WorldsUi.RULES_SUMMARY.length, 6);
  assert.match(WorldsUi.RULES_SUMMARY.join(' '), /Budget 100 crediti, \+5 dopo lo Swiss Stage/);
});
