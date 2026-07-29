const test = require('node:test');
const assert = require('node:assert/strict');

const {
  saveLineup,
  lineupViewModel
} = require('../js/lineup-ui.js');

test('saveLineup uses the matchday-independent command without a matchdayId', async () => {
  const calls = [];
  const api = async (path, options) => {
    calls.push({path, options});
    return {players: [], effectivePlayers: [], editable: true, nextEffectiveAt: null};
  };

  await saveLineup(api, 7, [11, 12, 13, 14, 15]);

  assert.deepEqual(calls, [{
    path: '/fanta-teams/7/formazioni/lineup',
    options: {
      method: 'PUT',
      body: JSON.stringify({titolariIds: [11, 12, 13, 14, 15]})
    }
  }]);
  assert.equal(JSON.parse(calls[0].options.body).matchdayId, undefined);
});

test('lineupViewModel keeps currently effective players separate from the pending Friday selection', () => {
  const response = {
    players: [
      {id: 21, nickname: 'New Top', role: 'TOP'},
      {id: 12, nickname: 'Old Jungle', role: 'JUNGLE'},
      {id: 13, nickname: 'Old Mid', role: 'MID'},
      {id: 14, nickname: 'Old Adc', role: 'ADC'},
      {id: 15, nickname: 'Old Support', role: 'SUPPORT'}
    ],
    effectivePlayers: [
      {id: 11, nickname: 'Old Top', role: 'TOP'},
      {id: 12, nickname: 'Old Jungle', role: 'JUNGLE'},
      {id: 13, nickname: 'Old Mid', role: 'MID'},
      {id: 14, nickname: 'Old Adc', role: 'ADC'},
      {id: 15, nickname: 'Old Support', role: 'SUPPORT'}
    ],
    nextEffectiveAt: '2026-07-30T22:00:00Z'
  };

  const view = lineupViewModel(response);

  assert.deepEqual(view.activePlayers.map(player => player.nickname), [
    'Old Top', 'Old Jungle', 'Old Mid', 'Old Adc', 'Old Support'
  ]);
  assert.deepEqual(view.pendingPlayers.map(player => player.nickname), [
    'New Top', 'Old Jungle', 'Old Mid', 'Old Adc', 'Old Support'
  ]);
  assert.equal(view.pendingEffectiveAt, '2026-07-30T22:00:00Z');
});

test('lineupViewModel does not label an already effective selection as pending', () => {
  const effective = [
    {id: 11, nickname: 'Top', role: 'TOP'},
    {id: 12, nickname: 'Jungle', role: 'JUNGLE'},
    {id: 13, nickname: 'Mid', role: 'MID'},
    {id: 14, nickname: 'Adc', role: 'ADC'},
    {id: 15, nickname: 'Support', role: 'SUPPORT'}
  ];

  const view = lineupViewModel({
    players: [...effective].reverse(),
    effectivePlayers: effective,
    nextEffectiveAt: '2026-08-06T22:00:00Z'
  });

  assert.deepEqual(view.activePlayers.map(player => player.id), [11, 12, 13, 14, 15]);
  assert.deepEqual(view.pendingPlayers, []);
  assert.equal(view.pendingEffectiveAt, null);
});
