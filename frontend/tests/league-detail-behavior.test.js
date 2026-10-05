const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const script = fs.readFileSync(path.join(__dirname, '../js/league-detail.js'), 'utf8');
const page = fs.readFileSync(path.join(__dirname, '../lega.html'), 'utf8');

function section(name) {
  return page.match(new RegExp(`<section class="league-view[^"]*" data-view="${name}">([\\s\\S]*?)</section>\\s*(?=<section class="league-view|</div>)`))?.[1] || '';
}

test('league page runs synchronization and countdown independently across every section', () => {
  assert.match(script, /function startPageSynchronization\(/);
  assert.match(script, /async function synchronizeLeaguePage\(/);
  assert.match(script, /function startCountdown\(/);
  assert.match(script, /startPageSynchronization\(\);\s*startCumulativeRefresh\(\);\s*startCountdown\(\);/);
  assert.match(script, /setInterval\(synchronizeLeaguePage, 2000\)/);
});

test('cumulative scoring stays on a dedicated low-frequency refresh', () => {
  const start = script.indexOf('async function synchronizeLeaguePage()');
  const end = script.indexOf('// --------------------------------------------------------------------------- asta');
  assert.ok(start >= 0 && end > start);
  assert.doesNotMatch(script.slice(start, end), /loadCumulative|refreshCumulativeData/);
  assert.match(script, /setInterval\(refreshCumulativeData, 90000\)/);
  assert.match(script, /state\.cumulativeRefreshErrorNotified = true/);
});

test('league data is loaded for the league edition and competition, never hard-coded to LEC', () => {
  assert.match(script, /CompetitionDataSource\.loadPlayers\(api, competition\(\), editionId\)/);
  assert.match(script, /CompetitionDataSource\.loadTeams\(api, competition\(\), editionId\)/);
  assert.match(script, /CompetitionDataSource\.loadStandings\(api, competition\(\)\)/);
  assert.match(script, /CompetitionDataSource\.loadCumulativeRanking\(api, state\.leagueId\)/);
  assert.match(script, /CompetitionDataSource\.loadSynchronization\(api, competition\(\)\)/);
  assert.doesNotMatch(script, /LecDataSource|\/lec\//);
  assert.match(script, /Classifica \$\{escapeHtml\(state\.league\.competition\)\}/);
});

test('live auction protects custom bids and hides reraises from the current leader', () => {
  assert.match(script, /LeagueUtils\.mergeBidDraft/);
  assert.match(script, /highestBidderId/);
  assert.match(script, /Sei il miglior offerente/);
  assert.match(script, /timer a 15 secondi/);
  assert.match(script, /addEventListener\('input'[\s\S]*?bidDraft/);
  assert.match(script, /LeagueUtils\.participantCreditBalances\(state\.leagueTeams, state\.activeAuction\)/);
  assert.match(script, /Saldo previsto/);
});

test('regional and WORLDS navigation are conditional on the league ruleset', () => {
  assert.match(page, /data-section="auction" data-ruleset="REGIONAL"/);
  assert.match(page, /data-section="market" data-ruleset="WORLDS"/);
  assert.match(script, /button\.classList\.toggle\('hidden', button\.dataset\.ruleset !== ruleset\)/);
  assert.match(script, /isWorlds\(\) \? Promise\.resolve\(null\) : api\(`\/auctions\/active/);
});

test('WORLDS market shows prices, team filter, per-team counters and transfer penalties', () => {
  const market = section('market');
  assert.match(market, /id="market-role"/);
  assert.match(market, /id="market-team"/);
  assert.match(market, /id="team-counters"/);
  assert.match(market, /id="transfer-status"/);
  assert.match(script, /WorldsUi\.teamCounters\(roster/);
  assert.match(script, /WorldsUi\.transfersLabel\(summary\)/);
  assert.match(script, /\/worlds\/fanta-teams\/\$\{state\.activeTeam\.id\}\/transfers/);
  assert.match(script, /penaltyPoints \? `−\$\{item\.penaltyPoints\} pt` : 'gratuito'/);
});

test('WORLDS formation lets the manager pick captain, vice and bench order', () => {
  assert.match(script, /function renderWorldsFormation\(/);
  assert.match(script, /Capitano \(×2\)/);
  assert.match(script, /Vice-capitano/);
  assert.match(script, /Panchina \$\{index \+ 1\}/);
  assert.match(script, /WorldsUi\.validateLineup\(/);
  assert.match(script, /panchinaIds, capitanoId: Number\(values\.captain\), viceCapitanoId: Number\(values\.vice\)/);
});

test('formation save remains visible in the dialog and can return to editing', () => {
  assert.match(page, /id="edit-formation-button"/);
  assert.match(script, /function renderFormationSummary\(/);
  assert.match(script, /state\.currentLineup = await LineupUi\.saveLineup/);
  assert.doesNotMatch(script, /LineupUi\.saveLineup[\s\S]{0,300}formation-dialog'\)\.close/);
  assert.match(script, /LineupUi\.lineupViewModel\(lineup\)/);
  assert.match(script, /ATTIVA ORA/);
  assert.match(script, /SALVATA · ATTIVA DA/);
});

test('competition views render standings, fantasy averages and selectable per-game statistics', () => {
  assert.match(page, /id="match-selector"/);
  assert.match(page, /id="game-selector"/);
  assert.match(script, /function renderCompetitionStandings/);
  assert.match(script, /function renderPlayerPerformances/);
  assert.match(script, /Vision \$\{player\.visionScore\}/);
  assert.match(script, /\$\{player\.cs\} CS/);
  assert.match(script, /MatchesView\.kdaLabel\(player\)/);
  assert.match(script, /Fantapunteggio/);
  assert.match(script, /game-fantasy-score/);
  assert.match(section('performance'), /CC BY-SA/);
});

test('ADMIN synchronization controls live in the standings section and only request a sync', () => {
  const standings = section('standings');
  assert.match(standings, /admin-sync-panel/);
  assert.match(standings, /sync-button/);
  assert.match(standings, /correction-form/);
  assert.doesNotMatch(section('performance'), /admin-sync-panel/);
  assert.match(script, /Sincronizzazione richiesta: lo scheduler la esegue entro pochi secondi/);
});

test('Overview ranking renders only fantasy teams and points, never player names', () => {
  const start = script.indexOf('function renderCumulativeRanking(');
  const end = script.indexOf('function renderCompetitionMatches(', start);
  const renderer = script.slice(start, end);
  assert.match(renderer, /team\.teamName/);
  assert.match(renderer, /overallTotal/);
  assert.doesNotMatch(renderer, /contributingPlayers|slot-contributors|cumulative-slots/);
});

test('matchday formations expose manager and global ADMIN confirmation controls', () => {
  assert.match(page, /id="confirm-formation-button"/);
  assert.match(script, /data-confirm-formation/);
  assert.match(script, /confirm-all/);
  assert.match(script, /state\.user\?\.role === 'ADMIN'/);
  assert.match(script, /Conferma tutte le squadre/);
  assert.match(script, /Genera calendario Worlds/);
});
