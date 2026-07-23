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
  assert.match(script, /startPageSynchronization\(\);startCountdown\(\)/);
  assert.doesNotMatch(script, /if\(section==='auction'\)startAuctionPolling/);
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
  assert.match(script, /state\.currentFormation=await api/);
  assert.doesNotMatch(script, /state\.currentFormation=await api[\s\S]{0,300}formation-dialog'\)\.close/);
  assert.match(script, /synchronizeLeaguePage\(\)/);
});
