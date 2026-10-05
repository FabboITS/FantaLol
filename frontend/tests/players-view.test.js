const test = require('node:test');
const assert = require('node:assert/strict');
const PlayersView = require('../js/players-view.js');

const players = [
  {id: 1, nickname: 'Faker', ruolo: 'MID', teamId: 2, teamNome: 'T1', teamSigla: 'T1', nazionalita: 'KR'},
  {id: 2, nickname: 'Keria', ruolo: 'SUPPORT', teamId: 2, teamNome: 'T1', teamSigla: 'T1'},
  {id: 3, nickname: 'Doran', ruolo: 'TOP', teamId: 2, teamNome: 'T1', teamSigla: 'T1'},
  {id: 4, nickname: 'Chovy', ruolo: 'MID', teamId: 1, teamNome: 'Gen.G', teamSigla: 'GEN'}
];
const teams = [{id: 1, nome: 'Gen.G', sigla: 'GEN', logoUrl: '/media/teams/gen-g.png'}, {id: 2, nome: 'T1', sigla: 'T1'}];

test('players are grouped by team and ordered by role', () => {
  const groups = PlayersView.groupByTeam(teams, players, {});
  assert.deepEqual(groups.map(group => group.team.nome), ['Gen.G', 'T1']);
  assert.deepEqual(groups[1].players.map(player => player.ruolo), ['TOP', 'MID', 'SUPPORT']);
  assert.equal(groups[0].team.logoUrl, '/media/teams/gen-g.png');
});

test('role filter and nickname/team search hide empty teams', () => {
  assert.deepEqual(PlayersView.groupByTeam(teams, players, {role: 'mid'}).map(group => group.players.length), [1, 1]);
  const search = PlayersView.groupByTeam(teams, players, {query: 'ker'});
  assert.deepEqual(search.map(g => g.players.map(p => p.nickname)), [['Faker', 'Keria']]);
  assert.deepEqual(PlayersView.groupByTeam(teams, players, {query: 'kr'}).map(g => g.players.map(p => p.nickname)), [['Faker']]);
  assert.deepEqual(PlayersView.groupByTeam(teams, players, {query: 'gen'})[0].players.map(p => p.nickname), ['Chovy']);
});

test('unknown teams fall back to the player team data', () => {
  const groups = PlayersView.groupByTeam([], [{id: 9, nickname: 'Solo', ruolo: 'ADC', teamId: 7, teamNome: 'Nuovi', teamSigla: 'NEW'}], {});
  assert.equal(groups[0].team.nome, 'Nuovi');
  assert.equal(groups[0].team.sigla, 'NEW');
});

test('graphic fallback uses initials on a stable colour', () => {
  assert.equal(PlayersView.initials('Hans Sama'), 'HS');
  assert.equal(PlayersView.initials('Faker'), 'FA');
  assert.equal(PlayersView.initials(''), '?');
  assert.equal(PlayersView.avatarColor('Faker'), PlayersView.avatarColor('Faker'));
  assert.match(PlayersView.avatarColor('Chovy'), /^#[0-9a-f]{6}$/);
});
