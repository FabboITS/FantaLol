const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const script = fs.readFileSync(path.join(__dirname, '../js/league-detail.js'), 'utf8');
const page = fs.readFileSync(path.join(__dirname, '../lega.html'), 'utf8');

test('league page runs synchronization and countdown independently across every section', () => {
  assert.match(script, /function startPageSynchronization\(/);
  assert.match(script, /function synchronizeLeaguePage\(/);
  assert.match(script, /function startCountdown\(/);
  assert.match(script, /startPageSynchronization\(\);startCumulativeRefresh\(\);startCountdown\(\)/);
  assert.doesNotMatch(script, /if\(section==='auction'\)startAuctionPolling/);
});

test('auction polling keeps cumulative scoring on a dedicated low-frequency refresh', () => {
  assert.match(script, /function startCumulativeRefresh\(/);
  assert.match(script, /setInterval\(refreshCumulativeData,90000\)/);
  assert.match(script, /function refreshCumulativeData\(/);
  assert.match(script, /LecDataSource\.loadCumulativePerformances\(api\)/);
  assert.match(script, /LecDataSource\.loadCumulativeRanking\(api,state\.leagueId\)/);
  const pollStart = script.indexOf('async function synchronizeLeaguePage()');
  const pollEnd = script.indexOf('function renderDashboardState()');
  assert.ok(pollStart >= 0 && pollEnd > pollStart);
  assert.doesNotMatch(script.slice(pollStart, pollEnd), /loadCumulative|refreshCumulativeData/);
  assert.match(script, /catch\(error\)\{if\(!state\.cumulativeRefreshErrorNotified\)\{toast\(`Fonte non disponibile: \$\{error\.message\}`,true\);state\.cumulativeRefreshErrorNotified=true\}\}finally\{state\.cumulativeRefreshPending=false\}/);
});

test('live auction protects custom bids and hides reraises from the current leader', () => {
  assert.match(script, /LeagueUtils\.mergeBidDraft/);
  assert.match(script, /highestBidderId/);
  assert.match(script, /Sei il miglior offerente/);
  assert.match(script, /timer a 15 secondi/);
  assert.match(script, /addEventListener\('input'.*bidDraft/s);
});

test('live auction renders synchronized participant credit balances', () => {
  assert.match(script, /function renderParticipantCredits\(/);
  assert.match(script, /LeagueUtils\.participantCreditBalances\(state\.leagueTeams,state\.activeAuction\)/);
  assert.match(script, /participant-credits/);
  assert.match(script, /Saldo previsto/);
  assert.match(script, /renderParticipantCredits\(\)/);
});

test('formation save remains visible in the dialog and can return to editing', () => {
  assert.match(page, /id="edit-formation-button"/);
  assert.match(script, /function renderFormationSummary\(/);
  assert.match(script, /state\.currentLineup=await LineupUi\.saveLineup/);
  assert.doesNotMatch(script, /LineupUi\.saveLineup[\s\S]{0,300}formation-dialog'\)\.close/);
  assert.match(script, /synchronizeLeaguePage\(\)/);
});

test('weekly lineup controls and pending status are independent from matchdays', () => {
  assert.doesNotMatch(page, /name="matchdayId"/);
  assert.match(page, /\/js\/lineup-ui\.js/);
  assert.match(script, /\/formazioni\/lineup/);
  assert.match(script, /rosterButton\.classList\.toggle\('hidden',!state\.activeTeam\|\|state\.activeTeam\.rosa\.length<5\|\|state\.league\.auctionOpen\)/);
  assert.doesNotMatch(script, /rosa\.length<5\|\|!state\.matchdays\.length/);
  assert.match(script, /LineupUi\.lineupViewModel\(lineup\)/);
  assert.match(script, /ATTIVA ORA/);
  assert.match(script, /SALVATA · ATTIVA DA/);
});

test('LEC views render standings, fantasy averages and selectable per-game statistics', () => {
  assert.match(page, /id="lec-match-selector"/);
  assert.match(page, /id="lec-game-selector"/);
  assert.match(script, /function renderLecStandings/);
  assert.match(script, /function renderPlayerPerformances/);
  assert.match(script, /Vision \$\{player\.visionScore\}/);
  assert.match(script, /\$\{player\.cs\} CS/);
  assert.match(script, /Perfetto/);
  assert.match(script, /player\.fantasyScore/);
  assert.match(script, /Fantapunteggio/);
  assert.match(script, /game-fantasy-score/);
  assert.doesNotMatch(script, /Fonte ufficiale non collegata|not-connected/);
});

test('league page renders cumulative standings, lineup window state, and ADMIN diagnostics hooks', () => {
  assert.match(script, /LecDataSource\.loadCumulativePerformances\(api\)/);
  assert.match(script, /LecDataSource\.loadCumulativeRanking\(api,state\.leagueId\)/);
  assert.match(script, /function renderCumulativeRanking\(/);
  assert.match(script, /function renderCumulativePerformances\(/);
  assert.match(script, /state\.user\?\.role==='ADMIN'/);
  assert.match(script, /function renderAdminDiagnostics\(/);
  assert.match(page, /id="lec-admin-panel"/);
  assert.match(page, /id="lec-sync-button"/);
  assert.match(page, /id="lec-correction-form"/);
  assert.match(page, /In attesa/);
  assert.match(page, /Provvisorio/);
  assert.match(page, /Aggiornato/);
  assert.match(page, /Fonte non disponibile/);
  assert.match(script, /Modifiche aperte da martedì a giovedì\./);
  assert.match(script, /La nuova formazione sarà valida da venerdì\./);
});

test('ADMIN synchronization controls are placed in the LEC standings section', () => {
  const html = page;
  const lecSection = html.match(/<section class="league-view hidden" data-view="lec">([\s\S]*?)<\/section>/)?.[1] || '';
  const performanceSection = html.match(/<section class="league-view hidden" data-view="performance">([\s\S]*?)<\/section>/)?.[1] || '';
  assert.match(lecSection, /lec-admin-panel/);
  assert.match(lecSection, /lec-sync-button/);
  assert.doesNotMatch(performanceSection, /lec-admin-panel/);
});

test('cumulative UI renders source freshness separately from team provisional scoring', () => {
  assert.match(script, /cumulativePerformanceSection/);
  assert.match(script, /cumulativeRankingSection/);
  assert.match(script, /LecDataSource\.cumulativeFreshnessLabel\(section\)/);
  assert.match(script, /cumulative-source-state/);
  assert.match(script, /team\.provisional\?'Formazione provvisoria/);
  assert.match(script, /state\.cumulativePerformances=performances\.items/);
  assert.match(script, /state\.cumulativeRanking=ranking\.items/);
});

test('Overview ranking renders only fantasy teams and points, never player names', () => {
  const start = script.indexOf('function renderCumulativeRanking(');
  const end = script.indexOf('function renderLecMatches(', start);
  const renderer = script.slice(start, end);
  assert.match(renderer, /team\.teamName/);
  assert.match(renderer, /overallAverage/);
  assert.doesNotMatch(renderer, /contributingPlayers|slot-contributors|cumulative-slots/);
});
