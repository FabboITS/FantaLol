const state = {
    token: localStorage.getItem('fantalol_token'),
    user: JSON.parse(localStorage.getItem('fantalol_user') || 'null'),
    leagueId: null,
    league: null,
    leagueTeams: [],
    mine: [],
    activeTeam: null,
    players: [],
    teams: [],
    matchdays: [],
    competitionMatches: [],
    cumulativePerformances: [],
    cumulativeRanking: [],
    cumulativePerformanceSection: {status: 'awaiting-data', lastUpdatedAt: null, provisional: true, items: []},
    cumulativeRankingSection: {status: 'awaiting-data', lastUpdatedAt: null, provisional: true, items: []},
    syncDiagnostics: null,
    activeAuction: null,
    market: null,
    transfers: null,
    marketFilters: {role: '', team: ''},
    synchronizationTimer: null,
    cumulativeRefreshTimer: null,
    countdownTimer: null,
    synchronizationPending: false,
    cumulativeRefreshPending: false,
    synchronizationErrorNotified: false,
    cumulativeRefreshErrorNotified: false,
    countdownExpired: false,
    bidDraft: null,
    auctionRenderKey: null,
    formationHistory: [],
    lineupWindow: null,
    currentLineup: null,
    activeFormationMatchdayId: null,
    confirmedMatchdays: new Set(),
    formationEditing: false,
    formationDirty: false,
    occupied: new Set(),
    activeSection: 'overview'
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'}[char]));
const roles = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

async function api(path, options = {}) {
    const headers = {'Content-Type': 'application/json', ...options.headers, Authorization: `Bearer ${state.token}`};
    const response = await fetch(`/api${path}`, {...options, headers});
    if (response.status === 204) return null;
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        if (response.status === 401) {
            logout(false);
            return null;
        }
        const details = data?.details?.join(' · ');
        throw new Error(details || data?.message || `Errore HTTP ${response.status}`);
    }
    return data;
}

function toast(message, error = false) {
    const element = $('#toast');
    element.textContent = message;
    element.className = `toast show${error ? ' error' : ''}`;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => element.className = 'toast', 3200);
}

function logout(notify = true) {
    localStorage.removeItem('fantalol_token');
    localStorage.removeItem('fantalol_user');
    if (notify) location.href = '/index.html?login=1#leagues';
    else location.replace('/index.html?login=1#leagues');
}

const isWorlds = () => state.league?.ruleset === 'WORLDS';
const competition = () => state.league?.competition || 'LEC';
function canManageLeague() { return state.user?.role === 'ADMIN' || state.league?.adminUsername === state.user?.username; }
function rosterLimit() { return state.league?.maxRosterSize ?? (state.league?.numeroSquadre <= 5 ? 10 : 5); }
function formatInstant(value) { return value ? new Date(value).toLocaleString('it-IT') : 'non disponibile'; }

function showError(message) {
    $('#league-loading').classList.add('hidden');
    $('#league-dashboard').classList.add('hidden');
    $('#league-error-message').textContent = message;
    $('#league-error').classList.remove('hidden');
}

// --------------------------------------------------------------------------- avvio
async function initialise() {
    if (!state.token || !state.user) {
        location.replace('/index.html?login=1#leagues');
        return;
    }
    $('#user-chip').textContent = `${state.user.username} · ${state.user.role}`;
    state.leagueId = LeagueUtils.parseLeagueId(location.search);
    if (!state.leagueId) {
        showError('Il link della lega non contiene un identificativo valido.');
        return;
    }
    try {
        const leagues = await api('/leagues');
        if (!leagues) return;
        state.league = leagues.find(league => Number(league.id) === state.leagueId);
        if (!state.league) {
            showError('Questa lega non esiste oppure non è accessibile dal tuo account.');
            return;
        }
        const editionId = state.league.editionId;
        const [leagueTeams, mine, players, teams, matchdays] = await Promise.all([
            api(`/fanta-teams/by-league/${state.leagueId}`),
            api('/fanta-teams/me'),
            CompetitionDataSource.loadPlayers(api, competition(), editionId),
            CompetitionDataSource.loadTeams(api, competition(), editionId),
            api(`/matchdays?leagueId=${state.leagueId}`)
        ]);
        if (!leagueTeams || !mine || !players || !teams || !matchdays) return;
        state.leagueTeams = leagueTeams;
        state.mine = mine;
        state.players = players;
        state.teams = teams;
        state.matchdays = matchdays.filter(day => Number(day.leagueId) === state.leagueId);
        state.activeTeam = mine.find(team => Number(team.leagueId) === state.leagueId) || null;
        applyRuleset();
        renderDashboard();
        await Promise.all([renderExternalData(), loadLineupWindow(), isWorlds() ? refreshMarket() : null]);
        $('#league-loading').classList.add('hidden');
        $('#league-dashboard').classList.remove('hidden');
        startPageSynchronization();
        startCumulativeRefresh();
        startCountdown();
    } catch (error) {
        showError(error.message);
    }
}

function applyRuleset() {
    const ruleset = state.league.ruleset;
    $$('[data-ruleset]').forEach(button => button.classList.toggle('hidden', button.dataset.ruleset !== ruleset));
    $('#league-competition').textContent = `${state.league.competition} · ${state.league.editionName || ''}`;
    $('#standings-nav').innerHTML = `<span>05</span> Classifica ${escapeHtml(state.league.competition)}`;
    $('#standings-title').textContent = `CLASSIFICA ${state.league.competition}`;
    $('#formation-kicker').textContent = isWorlds() ? 'Formazione di giornata' : 'Formazione settimanale';
}

async function loadLineupWindow() {
    if (!state.activeTeam) return;
    try {
        state.lineupWindow = await api(`/fanta-teams/${state.activeTeam.id}/formazioni/window`);
        renderMatchdays();
    } catch (error) {
        state.lineupWindow = null;
    }
}

// --------------------------------------------------------------------------- dashboard
function renderDashboard() {
    document.title = `${state.league.nome} — FantaLeague`;
    $('#league-name').textContent = state.league.nome;
    $('#league-admin').textContent = `Admin · ${state.league.adminUsername}`;
    $('#league-code').textContent = state.league.codiceInvito;
    $('#overview-title').textContent = state.league.nome;
    renderDashboardState();
    renderAuction();
}

function renderMetrics() {
    const creditLabel = isWorlds() ? 'Budget iniziale' : 'Crediti iniziali';
    $('#league-metrics').innerHTML = `<article class="metric-card"><span>Fantasy team</span><strong>${state.leagueTeams.length}</strong></article><article class="metric-card"><span>${creditLabel}</span><strong>${state.league.creditiIniziali}</strong></article><article class="metric-card"><span>Giornate</span><strong>${state.matchdays.length}</strong></article>`;
}

function renderDashboardState() {
    const auctionState = $('#auction-state');
    if (isWorlds()) {
        auctionState.textContent = 'Mercato a listone';
        auctionState.classList.add('open');
    } else {
        auctionState.textContent = state.league.auctionOpen ? 'Asta aperta' : 'Asta chiusa';
        auctionState.classList.toggle('open', state.league.auctionOpen);
    }
    renderMetrics();
    renderMatchdays();
    renderTeams();
    renderRanking();
}

function renderRanking() { renderCumulativeRanking(state.cumulativeRankingSection); }

function rosterSorted(team) {
    return [...(team.rosa || [])].sort((left, right) => roles.indexOf(left.ruolo) - roles.indexOf(right.ruolo) || left.lecPlayerNickname.localeCompare(right.lecPlayerNickname, 'it'));
}

function renderTeams() {
    $('#league-teams').innerHTML = state.leagueTeams.length ? state.leagueTeams.map(team => {
        const roster = rosterSorted(team);
        const cumulative = state.cumulativeRanking.find(score => Number(score.fantasyTeamId) === Number(team.id));
        const sourceProvisional = state.cumulativeRankingSection.provisional;
        const total = cumulative?.overallTotal;
        const scoreLabel = cumulative ? (cumulative.provisional && total == null ? 'Formazione provvisoria' : sourceProvisional ? `${Number(total).toFixed(2)} pt · Dati provvisori` : `${Number(total).toFixed(2)} pt`) : 'In attesa';
        const credits = isWorlds() ? `${team.creditiResidui} crediti disponibili` : `${team.creditiResidui} crediti rimasti`;
        return `<article class="league-team-card"><div class="team-card-head"><div><p>${escapeHtml(team.ownerUsername || 'Manager')}</p><h3>${escapeHtml(team.nome)}</h3><p>${credits}</p></div><strong class="team-points">${scoreLabel}</strong></div>${roster.length ? `<div class="roster-list">${roster.map(player => `<div class="roster-player"><span class="role">${escapeHtml(player.ruolo)}</span><strong>${escapeHtml(player.lecPlayerNickname)}</strong><small>${escapeHtml(player.teamNome || '')} · ${player.creditiSpesi} cr</small></div>`).join('')}</div>` : '<p class="empty-roster">Rosa ancora vuota</p>'}</article>`;
    }).join('') : '<p class="empty-list">Nessun fantasy team iscritto.</p>';
}

function confirmationWindowOpen() {
    return Boolean(state.lineupWindow ? state.lineupWindow.editable || isWorlds() : false);
}

function renderMatchdays() {
    const manager = canManageLeague();
    const createButton = $('#create-matchday-button');
    createButton.textContent = isWorlds() ? 'Genera calendario Worlds' : '+ Giornata';
    createButton.classList.toggle('hidden', !manager || (isWorlds() ? state.matchdays.length > 0 : state.matchdays.some(day => !day.chiusa)));
    const rosterButton = $('#open-formation-button');
    rosterButton.textContent = isWorlds() ? 'Formazione e capitano' : state.league.maxPerRole === 1 ? 'Vedi la tua rosa' : 'Modifica formazione';
    const minimum = isWorlds() ? 5 : 5;
    rosterButton.classList.toggle('hidden', !state.activeTeam || state.activeTeam.rosa.length < minimum || state.league.auctionOpen);
    const canConfirm = !isWorlds() && confirmationWindowOpen() && !state.league.auctionOpen;
    $('#matchdays-list').innerHTML = state.matchdays.length ? [...state.matchdays].sort((a, b) => b.numero - a.numero).map(day => {
        const status = day.chiusa ? 'Chiusa' : day.auctionLocked ? 'In attesa della chiusura asta' : day.status === 'WAITING_FOR_POSTPONED_MATCHES' ? 'In attesa di recuperi' : day.provisional ? 'Risultati provvisori' : 'Formazione aperta';
        const confirmed = state.confirmedMatchdays.has(Number(day.id));
        const managerActions = state.activeTeam && !day.chiusa && !state.league.auctionOpen ? `<button class="button button-ghost" data-open-formation="${day.id}">Rosa</button>${isWorlds() ? '' : confirmed ? '<span class="formation-confirmed-label">Rosa confermata</span>' : canConfirm ? `<button class="button button-primary" data-confirm-formation="${day.id}">Conferma rosa</button>` : ''}` : '';
        const adminAction = state.user?.role === 'ADMIN' && !isWorlds() && !day.chiusa && !state.league.auctionOpen && canConfirm ? `<button class="button button-ghost" data-confirm-all-formations="${day.id}">Conferma tutte le squadre</button>` : '';
        const window = day.startsAt ? ` · ${new Date(day.startsAt).toLocaleDateString('it-IT')}${day.endsAt ? ` → ${new Date(day.endsAt).toLocaleDateString('it-IT')}` : ''}` : day.data ? ` · ${escapeHtml(day.data)}` : '';
        return `<article class="matchday-card"><div><h3>Giornata ${day.numero}</h3><p>${escapeHtml(day.descrizione || 'Giornata di lega')}${window}</p></div><span class="day-status ${day.chiusa ? 'closed' : ''}">${status}</span><div class="matchday-actions">${managerActions}${adminAction}</div></article>`;
    }).join('') : `<div class="integration-state"><span class="integration-icon">◇</span><h3>Nessuna giornata</h3><p>${isWorlds() ? 'L’admin della lega genera le 8 giornate Worlds (Swiss Round 1–5, quarti, semifinali, finale) dal calendario ufficiale.' : 'La formazione settimanale può essere gestita anche prima della prima giornata.'}</p></div>`;
}

// --------------------------------------------------------------------------- dati della competizione
async function renderExternalData() {
    try {
        const [standings, matches] = await Promise.all([
            CompetitionDataSource.loadStandings(api, competition()),
            CompetitionDataSource.loadMatches(api, competition())
        ]);
        renderCompetitionStandings(standings);
        renderCompetitionMatches(matches);
    } catch (error) {
        toast(`Fonte non disponibile: ${error.message}`, true);
    }
    await refreshCumulativeData();
    if (state.user?.role === 'ADMIN') {
        try {
            await loadAdminDiagnostics();
        } catch (error) {
            renderAdminDiagnosticError(error);
        }
    }
}

function freshnessLabel(data) {
    if (data.status === 'stale') return `Ultimo aggiornamento ${data.lastUpdatedAt ? new Date(data.lastUpdatedAt).toLocaleString('it-IT') : 'non disponibile'} · dati temporaneamente non aggiornati`;
    return data.lastUpdatedAt ? `Aggiornato ${new Date(data.lastUpdatedAt).toLocaleString('it-IT')}` : 'Sincronizzazione in attesa';
}

function renderCompetitionStandings(data) {
    const target = $('#competition-standings');
    if (!data.items?.length) {
        renderIntegrationState('#competition-standings', 'Classifica in attesa', 'I dati appariranno dopo la prima sincronizzazione PandaScore.');
        return;
    }
    target.className = 'lec-data-card';
    target.innerHTML = `<div class="lec-meta">${escapeHtml(freshnessLabel(data))}${data.provisional ? ' · ordine provvisorio' : ''}</div><div class="lec-table">${data.items.map(team => `<article class="lec-standing-row"><b>${String(team.position).padStart(2, '0')}</b><strong>${escapeHtml(team.teamName)}</strong><span>${team.seriesWins} V</span><span>${team.seriesLosses} P</span></article>`).join('')}</div>`;
}

function renderCumulativePerformances(section) {
    const target = $('#fantasy-performance');
    const players = section?.items || [];
    const sourceLabel = CompetitionDataSource.cumulativeFreshnessLabel(section);
    if (!players.length) {
        target.innerHTML = `<div class="integration-state"><h3>In attesa</h3><p>${escapeHtml(sourceLabel)}. Le medie cumulative appariranno dopo le prime statistiche Leaguepedia.</p></div>`;
        return;
    }
    target.innerHTML = `<div class="lec-data-card"><div class="performance-heading"><div><p class="eyebrow">Media cumulativa ${escapeHtml(competition())}</p><h3>FANTAPUNTEGGIO</h3></div><small>${escapeHtml(sourceLabel)}</small></div>${players.map((player, index) => `<article class="fantasy-player-row"><b>${String(index + 1).padStart(2, '0')}</b><div><strong>${escapeHtml(player.nickname)}</strong><small>${escapeHtml(player.role)} · ${player.gamesPlayed} game giocati · ${player.status === 'available' ? 'Aggiornato' : 'In attesa'}</small></div><em>${player.average == null ? 'In attesa' : `${Number(player.average).toFixed(2)} pt`}</em></article>`).join('')}</div>`;
}

function renderPlayerPerformances(data) { renderCumulativePerformances(data); }

function renderCumulativeRanking(section) {
    const target = $('#fantasy-ranking');
    const ranked = LeagueUtils.rankCumulativeTeams(section?.items || []);
    const sourceLabel = CompetitionDataSource.cumulativeFreshnessLabel(section);
    if (!ranked.length) {
        target.innerHTML = `<p class="empty-list">${escapeHtml(sourceLabel)} · punteggi cumulativi non ancora disponibili.</p>`;
        return;
    }
    const detail = team => isWorlds() ? `Miglior giornata ${Number(team.bestMatchday || 0).toFixed(1)} · capitani ${Number(team.captainPoints || 0).toFixed(1)}` : team.provisional ? 'Formazione provvisoria' : 'Formazione completa';
    const points = team => team.overallTotal == null ? 'In attesa' : `${Number(team.overallTotal).toFixed(2)} pt`;
    target.innerHTML = `<div class="cumulative-source-state">${escapeHtml(sourceLabel)}</div>${ranked.map((team, index) => `<article class="ranking-row"><span class="rank">${String(index + 1).padStart(2, '0')}</span><span class="ranking-team"><strong>${escapeHtml(team.teamName)}</strong><small>${escapeHtml(detail(team))}</small></span><strong class="ranking-points">${points(team)}</strong></article>`).join('')}`;
}

function renderCompetitionMatches(data) {
    state.competitionMatches = data.items || [];
    const matchSelect = $('#match-selector');
    if (!state.competitionMatches.length) {
        matchSelect.innerHTML = '<option>Nessuna partita con statistiche</option>';
        $('#game-selector').innerHTML = '';
        $('#game-performance').innerHTML = '<p class="empty-list">Statistiche per-game in attesa.</p>';
        return;
    }
    matchSelect.innerHTML = state.competitionMatches.map(match => `<option value="${escapeHtml(match.id)}">${escapeHtml(match.name)}${match.date ? ` · ${escapeHtml(match.date)}` : ''}</option>`).join('');
    renderSelectedMatch();
}

function selectedMatch() {
    return state.competitionMatches.find(item => String(item.id) === String($('#match-selector').value)) || state.competitionMatches[0];
}

function renderSelectedMatch() {
    const match = selectedMatch();
    $('#game-selector').innerHTML = (match?.games || []).map(game => `<option value="${escapeHtml(game.id)}">${escapeHtml(game.label)}</option>`).join('');
    renderSelectedGame();
}

function renderSelectedGame() {
    const match = selectedMatch();
    const game = match?.games?.find(item => String(item.id) === String($('#game-selector').value)) || match?.games?.[0];
    const target = $('#game-performance');
    if (!game) {
        target.innerHTML = '<p class="empty-list">Statistiche non ancora disponibili.</p>';
        return;
    }
    target.innerHTML = MatchesView.groupPlayersByTeam(game.players).map(({team, players}) => `<section class="game-team"><h3>${escapeHtml(team)}</h3>${players.map(player => `<article class="game-player-row"><div><img src="${escapeHtml(player.championImagePath)}" alt="${escapeHtml(player.championName)}"><strong>${escapeHtml(player.nickname)}</strong><small>${escapeHtml(player.championName)}</small></div><b>${player.kills}/${player.deaths}/${player.assists}</b><span>${player.role === 'SUPPORT' ? `Vision ${player.visionScore}` : `${player.cs} CS`}</span><em>KDA ${MatchesView.kdaLabel(player)}</em><b class="game-fantasy-score">Fantapunteggio ${player.fantasyScore == null ? 'In attesa' : `${Number(player.fantasyScore).toFixed(2)} pt`}</b></article>`).join('')}</section>`).join('');
}

function renderIntegrationState(selector, title, copy) {
    $(selector).className = 'integration-state';
    $(selector).innerHTML = `<span class="integration-icon">⌁</span><h3>${title}</h3><p>${copy}</p><span class="integration-label">Sincronizzazione automatica</span>`;
}

// --------------------------------------------------------------------------- diagnostica ADMIN
function diagnosticLabel(status, provisional = false) {
    if ((status === 'available' || status === 'fresh' || status === 'SUCCESS') && !provisional) return 'Aggiornato';
    if (provisional || status === 'stale') return 'Provvisorio';
    if (status === 'unavailable' || status === 'failed' || status === 'FAILED') return 'Fonte non disponibile';
    return 'In attesa';
}

async function loadAdminDiagnostics() {
    state.syncDiagnostics = await CompetitionDataSource.loadSynchronization(api, competition());
    renderAdminDiagnostics(state.syncDiagnostics);
}

function renderAdminDiagnostics(data) {
    const panel = $('#admin-sync-panel');
    panel.classList.toggle('hidden', state.user?.role !== 'ADMIN');
    if (state.user?.role !== 'ADMIN' || !data) return;
    const status = diagnosticLabel(data.status, data.provisional);
    const label = $('#sync-state');
    label.textContent = `${status} · ultimo aggiornamento ${formatInstant(data.lastUpdatedAt)}`;
    label.className = `admin-state ${status === 'Aggiornato' ? 'available' : status === 'Provvisorio' ? 'provisional' : ''}`;
    const counts = data.counts || {};
    const providers = (data.providers || []).map(provider => `<article><strong>${escapeHtml(provider.provider)}</strong><span>${escapeHtml(diagnosticLabel(provider.status))}</span><small>Ultimo tentativo: ${escapeHtml(formatInstant(provider.lastAttemptAt))}${provider.lastError ? ` · ${escapeHtml(provider.lastError)}` : ''}</small></article>`).join('') || '<p class="admin-meta">In attesa dello stato dei provider.</p>';
    const unmatched = (data.unmatchedPlayers || []).length ? `<section class="unmatched-list"><strong>Player Leaguepedia non associati</strong><p class="admin-meta">${escapeHtml(data.unmatchedPlayers.join(', '))}</p></section>` : '';
    $('#sync-diagnostics').innerHTML = `<section class="diagnostic-grid"><article><span>Game inseriti</span><strong>${Number(counts.insertedGames || 0)}</strong></article><article><span>Game aggiornati</span><strong>${Number(counts.updatedGames || 0)}</strong></article><article><span>Game ignorati</span><strong>${Number(counts.skippedGames || 0)}</strong></article><article><span>Errori import</span><strong>${Number(counts.failedGames || 0)}</strong></article></section><section class="provider-status">${providers}</section>${unmatched}`;
}

function renderAdminDiagnosticError(error) {
    const panel = $('#admin-sync-panel');
    if (state.user?.role !== 'ADMIN') return;
    panel.classList.remove('hidden');
    const label = $('#sync-state');
    label.textContent = `Fonte non disponibile · ${error.message}`;
    label.className = 'admin-state';
    toast(`Fonte non disponibile: ${error.message}`, true);
}

function optionalNumber(value) { return value === '' ? null : Number(value); }
function optionalBoolean(value) { return value === '' ? null : value === 'true'; }

// --------------------------------------------------------------------------- sezioni e sincronizzazione
function setSection(section) {
    state.activeSection = section;
    $$('[data-view]').forEach(view => view.classList.toggle('hidden', view.dataset.view !== section));
    $$('[data-section]').forEach(button => {
        const active = button.dataset.section === section;
        button.classList.toggle('active', active);
        if (active) button.setAttribute('aria-current', 'page');
        else button.removeAttribute('aria-current');
    });
}

function startPageSynchronization() {
    stopPageSynchronization();
    synchronizeLeaguePage();
    state.synchronizationTimer = setInterval(synchronizeLeaguePage, 2000);
}
function stopPageSynchronization() { clearInterval(state.synchronizationTimer); state.synchronizationTimer = null; }
function startCumulativeRefresh() { stopCumulativeRefresh(); state.cumulativeRefreshTimer = setInterval(refreshCumulativeData, 90000); }
function stopCumulativeRefresh() { clearInterval(state.cumulativeRefreshTimer); state.cumulativeRefreshTimer = null; }

async function refreshCumulativeData() {
    if (state.cumulativeRefreshPending) return;
    state.cumulativeRefreshPending = true;
    try {
        const [performances, ranking] = await Promise.all([
            CompetitionDataSource.loadCumulativePerformances(api, competition()),
            CompetitionDataSource.loadCumulativeRanking(api, state.leagueId)
        ]);
        state.cumulativePerformanceSection = performances;
        state.cumulativeRankingSection = ranking;
        state.cumulativePerformances = performances.items;
        state.cumulativeRanking = ranking.items;
        renderCumulativePerformances(performances);
        renderCumulativeRanking(ranking);
        renderTeams();
        state.cumulativeRefreshErrorNotified = false;
    } catch (error) {
        if (!state.cumulativeRefreshErrorNotified) {
            toast(`Fonte non disponibile: ${error.message}`, true);
            state.cumulativeRefreshErrorNotified = true;
        }
    } finally {
        state.cumulativeRefreshPending = false;
    }
}

function startCountdown() { stopCountdown(); state.countdownTimer = setInterval(renderCountdown, 100); }
function stopCountdown() { clearInterval(state.countdownTimer); state.countdownTimer = null; }

function auctionStateKey() {
    const auction = state.activeAuction;
    return JSON.stringify([state.league?.auctionOpen, state.activeTeam?.id, state.activeTeam?.creditiResidui, state.activeTeam?.rosa?.length, auction?.id, auction?.currentBid, auction?.highestBidderId, auction?.endsAt]);
}

async function synchronizeLeaguePage() {
    if (state.synchronizationPending) return;
    state.synchronizationPending = true;
    try {
        const [leagueTeams, auction, leagues, matchdays] = await Promise.all([
            api(`/fanta-teams/by-league/${state.leagueId}`),
            isWorlds() ? Promise.resolve(null) : api(`/auctions/active?leagueId=${state.leagueId}`),
            api('/leagues'),
            api(`/matchdays?leagueId=${state.leagueId}`)
        ]);
        if (!leagueTeams || !leagues || !matchdays) return;
        state.leagueTeams = leagueTeams;
        state.activeAuction = auction;
        state.league = leagues.find(league => Number(league.id) === state.leagueId) || state.league;
        state.matchdays = matchdays.filter(day => Number(day.leagueId) === state.leagueId);
        state.activeTeam = leagueTeams.find(team => team.id === state.activeTeam?.id) || state.activeTeam;
        state.occupied = new Set(leagueTeams.flatMap(team => team.rosa || []).map(entry => entry.lecPlayerId));
        state.bidDraft = LeagueUtils.mergeBidDraft(state.bidDraft, auction, state.activeTeam);
        const nextKey = auctionStateKey();
        if (nextKey !== state.auctionRenderKey) {
            renderAuction();
            state.auctionRenderKey = nextKey;
        }
        renderDashboardState();
        if ($('#formation-dialog').open && !state.formationDirty) await refreshOpenFormation();
        state.synchronizationErrorNotified = false;
    } catch (error) {
        if (!state.synchronizationErrorNotified) {
            toast(error.message, true);
            state.synchronizationErrorNotified = true;
        }
    } finally {
        state.synchronizationPending = false;
    }
}

// --------------------------------------------------------------------------- asta (regionale)
function renderCountdown() {
    const countdown = $('#auction-summary .countdown');
    if (!countdown || !state.activeAuction) return;
    const seconds = LeagueUtils.remainingAuctionSeconds(state.activeAuction.endsAt);
    countdown.textContent = `${seconds.toFixed(1)}s`;
    if (seconds === 0 && !state.countdownExpired) {
        state.countdownExpired = true;
        synchronizeLeaguePage();
    } else if (seconds > 0) {
        state.countdownExpired = false;
    }
}

function renderParticipantCredits() {
    const participants = LeagueUtils.participantCreditBalances(state.leagueTeams, state.activeAuction);
    if (!participants.length) return '<section class="participant-credits"><p class="participant-credits-empty">Nessun partecipante.</p></section>';
    return `<section class="participant-credits"><div class="participant-credits-heading"><span>Crediti partecipanti</span><small>Saldo aggiornato durante l’asta</small></div><div class="participant-credits-list">${participants.map(team => `<article class="participant-credit ${team.isProjected ? 'projected' : ''}"><div><strong>${escapeHtml(team.nome)}</strong><span>${escapeHtml(team.ownerUsername || 'Manager')}</span></div><div class="participant-credit-balance"><b>${team.displayCredits}</b><span>${team.isProjected ? 'Saldo previsto' : 'Crediti rimasti'}</span></div></article>`).join('')}</div></section>`;
}

function renderAuction() {
    if (isWorlds()) return;
    const team = state.activeTeam;
    const auction = state.activeAuction;
    const manager = canManageLeague();
    const open = state.league.auctionOpen;
    $('#auction-phase-controls').innerHTML = `<span class="auction-phase-${open ? 'open' : 'closed'}">${open ? 'Asta aperta' : 'Asta chiusa'}</span>${manager ? `<button class="button ${open ? 'button-danger' : 'button-primary'}" data-auction-phase="${open ? 'close' : 'open'}">${open ? 'Termina asta' : 'Avvia asta'}</button>` : ''}`;
    $('#auto-complete-button').classList.toggle('hidden', open || !manager || !team);
    if (!team) {
        $('#auction-summary').innerHTML = `<strong>Modalità spettatore</strong><span>Entra nella lega con il codice invito per partecipare.</span>${renderParticipantCredits()}`;
        $('#auction-list').innerHTML = '<p class="auction-wait">Puoi seguire lo stato dell’asta, ma non effettuare operazioni.</p>';
        return;
    }
    state.bidDraft = LeagueUtils.mergeBidDraft(state.bidDraft, auction, team);
    const view = auction ? LeagueUtils.auctionViewState(auction, team, state.bidDraft) : null;
    const bidControls = auction && open ? (view.isCurrentLeader ? '<p class="bid-leading">Sei il miglior offerente</p>' : `<form data-bid="${auction.id}"><input type="number" name="credits" min="${view.nextMinimum}" value="${state.bidDraft}" max="${team.creditiResidui}" ${view.canAfford ? '' : 'disabled'}><button class="button button-primary" ${view.canBid ? '' : 'disabled'}>Rilancia</button>${view.canAfford ? '' : '<p class="bid-unavailable">Non hai abbastanza crediti per rilanciare</p>'}</form>`) : '';
    const auctionDetails = auction ? `<div class="live-auction"><span class="live-dot"></span><strong>${escapeHtml(auction.playerNickname)}</strong><span>Offerta: <b>${auction.currentBid}</b></span><span>Leader: <b>${escapeHtml(auction.highestBidderName || '—')}</b></span><span class="countdown">${LeagueUtils.remainingAuctionSeconds(auction.endsAt).toFixed(1)}s</span>${bidControls}</div>` : `<strong>${escapeHtml(team.nome)}</strong><span>${team.creditiResidui} crediti disponibili</span><span>${team.rosa.length}/${rosterLimit()} player</span>`;
    $('#auction-summary').innerHTML = `${auctionDetails}${renderParticipantCredits()}`;
    if (!open) {
        $('#auction-list').innerHTML = '<p class="auction-wait">Il creatore della lega deve avviare l’asta per consentire nomine e rilanci.</p>';
        return;
    }
    $('#auction-list').innerHTML = auction ? '<p class="auction-wait">Ogni rilancio riavvia il timer a 15 secondi; allo scadere il player va al miglior offerente.</p>' : state.players.map(player => {
        const mine = team.rosa.find(entry => entry.lecPlayerId === player.id);
        const taken = state.occupied.has(player.id) && !mine;
        return `<article class="auction-row ${taken ? 'taken' : ''}"><div><span class="role">${escapeHtml(player.ruolo)}</span><strong>${escapeHtml(player.nickname)}</strong><small>${escapeHtml(player.teamNome)} · base ${player.quotazione}</small></div>${mine ? `<button class="button button-ghost" data-release="${mine.id}">Rilascia</button>` : taken ? '<span class="sold">ASSEGNATO</span>' : `<button class="button button-primary" data-start-auction="${player.id}" ${team.rosa.length >= rosterLimit() || team.creditiResidui < player.quotazione ? 'disabled' : ''}>Avvia asta · ${player.quotazione}</button>`}</article>`;
    }).join('');
}

// --------------------------------------------------------------------------- listone e cambi (WORLDS)
async function refreshMarket() {
    if (!isWorlds()) return;
    try {
        const [market, transfers] = await Promise.all([
            api(`/worlds/leagues/${state.leagueId}/market`),
            state.activeTeam ? api(`/worlds/fanta-teams/${state.activeTeam.id}/transfers`) : Promise.resolve(null)
        ]);
        state.market = market;
        state.transfers = transfers;
        renderMarket();
    } catch (error) {
        toast(error.message, true);
    }
}

function renderMarket() {
    const market = state.market;
    if (!market) return;
    const summary = state.transfers;
    const team = state.activeTeam;
    $('#market-phase').textContent = `${market.stage || 'Pre-torneo'} · max ${market.maxPlayersPerTeam ?? '—'} per team`;
    $('#transfer-status').textContent = team ? WorldsUi.transfersLabel(summary) : 'Modalità spettatore: entra nella lega per comprare dal listone.';
    $('#market-credits').textContent = summary ? `Crediti disponibili ${summary.credits} su un budget di ${summary.budget}${market.listonePublished ? '' : ' · listone non ancora pubblicato (solo squadre qualificate direttamente)'}` : '';
    const roster = team?.rosa || [];
    $('#team-counters').innerHTML = WorldsUi.teamCounters(roster, summary?.maxPlayersPerTeam ?? market.maxPlayersPerTeam).map(counter => `<span class="team-counter ${counter.over ? 'over' : ''}">${escapeHtml(counter.team)} ${counter.count}/${counter.limit ?? '—'}</span>`).join('') || '<span class="team-counter">Rosa vuota</span>';
    const teamSelect = $('#market-team');
    const teams = [...new Map(market.items.map(item => [item.teamId, item.teamNome])).entries()];
    const currentTeam = state.marketFilters.team;
    teamSelect.innerHTML = '<option value="">Tutti i team</option>' + teams.map(([id, name]) => `<option value="${id}" ${String(id) === String(currentTeam) ? 'selected' : ''}>${escapeHtml(name)}</option>`).join('');
    const sell = $('#market-sell');
    const previousSell = sell.value;
    sell.innerHTML = '<option value="">Nessuna vendita (slot libero)</option>' + rosterSorted({rosa: roster}).map(entry => `<option value="${entry.lecPlayerId}" ${String(entry.lecPlayerId) === previousSell ? 'selected' : ''}>Vendi ${escapeHtml(entry.lecPlayerNickname)} (${escapeHtml(entry.ruolo)} · ${entry.quotazione ?? entry.creditiSpesi} cr)</option>`).join('');
    const owned = new Set(roster.map(entry => entry.lecPlayerId));
    const rows = WorldsUi.marketRows(market.items, state.marketFilters);
    $('#market-list').innerHTML = rows.length ? rows.map(item => `<article class="market-row ${owned.has(item.id) ? 'owned' : ''} ${item.eliminated ? 'eliminated' : ''}"><span class="role">${escapeHtml(item.ruolo)}</span><div><strong>${escapeHtml(item.nickname)}</strong><small> · ${escapeHtml(item.teamNome)}${item.eliminated ? ' · eliminata' : ''}</small></div><span>${escapeHtml(item.teamSigla || '')}</span><strong>${item.quotazione} cr</strong>${!team ? '<span></span>' : owned.has(item.id) ? `<button class="button button-ghost" data-sell="${item.id}">Vendi</button>` : `<button class="button button-primary" data-buy="${item.id}">${sell.value ? 'Scambia' : 'Compra'}</button>`}</article>`).join('') : '<p class="empty-list">Nessun player nel listone per questi filtri.</p>';
    $('#transfer-history').innerHTML = summary?.items?.length ? `<h4>Storico cambi</h4>${summary.items.map(item => `<article><span>${item.playerOutNickname ? `${escapeHtml(item.playerOutNickname)} → ` : ''}${escapeHtml(item.playerInNickname || 'vendita')}</span><span class="${item.penaltyPoints ? 'penalty' : ''}">${item.penaltyPoints ? `−${item.penaltyPoints} pt` : 'gratuito'}</span></article>`).join('')}` : '';
}

async function makeTransfer(playerInId, playerOutId) {
    try {
        const transfer = await api(`/worlds/fanta-teams/${state.activeTeam.id}/transfers`, {method: 'POST', body: JSON.stringify({playerInId, playerOutId})});
        toast(transfer.penaltyPoints ? `Cambio effettuato: −${transfer.penaltyPoints} punti` : 'Cambio effettuato');
        $('#market-sell').value = '';
        await synchronizeLeaguePage();
        await refreshMarket();
    } catch (error) {
        toast(error.message, true);
    }
}

// --------------------------------------------------------------------------- formazione
async function openFormation(matchdayId = null) {
    if (!state.activeTeam || state.league.auctionOpen) {
        toast('Termina l’asta prima di usare la rosa.', true);
        return;
    }
    state.activeFormationMatchdayId = Number(matchdayId || state.matchdays[0]?.id || 0) || null;
    const [history, lineup, windowState] = await Promise.all([
        api(`/fanta-teams/${state.activeTeam.id}/formazioni`),
        api(`/fanta-teams/${state.activeTeam.id}/formazioni/lineup`),
        api(`/fanta-teams/${state.activeTeam.id}/formazioni/window`)
    ]);
    state.formationHistory = history || [];
    state.currentLineup = lineup;
    state.lineupWindow = windowState;
    state.confirmedMatchdays = new Set(state.formationHistory.filter(item => item.confirmed).map(item => Number(item.matchdayId)));
    state.formationEditing = isWorlds() || !(lineup?.players?.length || lineup?.effectivePlayers?.length);
    state.formationDirty = false;
    renderFormationDialog();
    $('#formation-dialog').showModal();
}

function latestFormation() { return [...state.formationHistory].reverse().find(item => item.source !== 'MISSING') || null; }
function formationWindowState() { return LeagueUtils.lineupWindowState(state.currentLineup, state.formationHistory, state.lineupWindow); }
function formationIsEditable() { return formationWindowState().editable; }

function renderFormationDialog() {
    const editable = formationIsEditable();
    if (isWorlds()) {
        renderWorldsFormation();
    } else {
        const showSummary = Boolean((state.currentLineup?.players?.length || state.currentLineup?.effectivePlayers?.length) && !state.formationEditing);
        if (showSummary) renderFormationSummary(state.currentLineup);
        else renderFormationSelectors(editable);
        $('#formation-form button[type=submit]').classList.toggle('hidden', !editable || showSummary);
        $('#edit-formation-button').classList.toggle('hidden', !editable || !showSummary);
    }
    const confirmButton = $('#confirm-formation-button');
    const confirmed = state.confirmedMatchdays.has(Number(state.activeFormationMatchdayId));
    const open = !isWorlds() && confirmationWindowOpen() && !state.league.auctionOpen;
    confirmButton.classList.toggle('hidden', !state.activeFormationMatchdayId || !open);
    confirmButton.disabled = confirmed;
    confirmButton.textContent = confirmed ? 'Rosa confermata' : 'Conferma rosa';
    $('#roster-history').innerHTML = renderRosterHistory(state.formationHistory);
}

function lineupWindowCopy() {
    const windowState = formationWindowState();
    const effective = windowState.nextEffectiveAt ? ` Prossima efficacia: ${formatInstant(windowState.nextEffectiveAt)}.` : '';
    const reason = state.lineupWindow?.reason || (state.league.competition === 'LEC' ? 'Modifiche aperte da martedì a giovedì. La nuova formazione sarà valida da venerdì.' : 'Modificabile fino a 60 minuti prima della prima serie della giornata.');
    return `${windowState.editable ? 'Modifiche aperte.' : 'Modifiche chiuse.'} ${reason}${effective}`;
}

function lineupCards(players) {
    return players.map(player => `<article class="formation-role-card formation-selected"><span>${escapeHtml(player.role)}</span><strong>${escapeHtml(player.nickname)}</strong></article>`).join('');
}

function renderFormationSummary(lineup) {
    const view = LineupUi.lineupViewModel(lineup);
    const active = view.activePlayers.length ? lineupCards(view.activePlayers) : '<p class="empty-roster">Nessuna formazione è ancora attiva.</p>';
    const pending = view.pendingPlayers.length ? `<section class="lineup-state pending"><h3>SALVATA · ATTIVA DA ${escapeHtml(formatInstant(view.pendingEffectiveAt))}</h3>${lineupCards(view.pendingPlayers)}</section>` : '';
    $('#formation-status').textContent = `${view.pendingPlayers.length ? 'La nuova formazione è salvata ma non è ancora attiva.' : 'Questa è la formazione attiva in questo momento.'} ${lineupWindowCopy()}`;
    $('#formation-roles').innerHTML = `<section class="lineup-state active"><h3>ATTIVA ORA</h3>${active}</section>${pending}`;
}

function renderFormationSelectors(editable) {
    const templatePlayers = state.currentLineup?.players?.length ? state.currentLineup.players : state.currentLineup?.effectivePlayers?.length ? state.currentLineup.effectivePlayers : latestFormation()?.players || [];
    const selectedByRole = new Map(templatePlayers.map(player => [player.role, String(player.id)]));
    $('#formation-status').textContent = editable ? `Scegli un player per ogni ruolo. Se non salvi, resta valida la formazione attiva. ${lineupWindowCopy()}` : `La formazione coincide automaticamente con i cinque player della tua rosa. ${lineupWindowCopy()}`;
    $('#formation-roles').innerHTML = roles.map(role => {
        const players = state.activeTeam.rosa.filter(entry => entry.ruolo === role);
        if (!editable) {
            const player = players[0];
            return `<article class="formation-role-card"><span>${role}</span><strong>${escapeHtml(player?.lecPlayerNickname || 'Non assegnato')}</strong></article>`;
        }
        return `<label>${role}<select name="role-${role}" required><option value="">Seleziona</option>${players.map(player => `<option value="${player.lecPlayerId}" ${selectedByRole.get(role) === String(player.lecPlayerId) ? 'selected' : ''}>${escapeHtml(player.lecPlayerNickname)}</option>`).join('')}</select></label>`;
    }).join('');
}

function renderWorldsFormation() {
    const lineup = state.currentLineup || {};
    const roster = rosterSorted(state.activeTeam);
    const starters = new Map((lineup.players || []).map(player => [player.role, String(player.id)]));
    const bench = (lineup.bench || []).map(player => String(player.id));
    const options = (selected, list = roster) => `<option value="">Seleziona</option>${list.map(entry => `<option value="${entry.lecPlayerId}" ${String(selected) === String(entry.lecPlayerId) ? 'selected' : ''}>${escapeHtml(entry.lecPlayerNickname)} · ${escapeHtml(entry.ruolo)} · ${escapeHtml(entry.teamNome || '')}</option>`).join('')}`;
    const lock = lineup.lockAt ? ` Blocco alle ${formatInstant(lineup.lockAt)}.` : '';
    $('#formation-status').textContent = lineup.targetMatchdayId ? `Formazione per la giornata ${state.matchdays.find(day => day.id === lineup.targetMatchdayId)?.numero ?? ''}.${lock} ${lineup.reason || ''}` : 'Calendario Worlds non ancora disponibile: la formazione si potrà salvare quando le giornate saranno generate.';
    $('#formation-roles').innerHTML = `<div class="worlds-lineup">${roles.map(role => `<label>${role}<select name="role-${role}" required>${options(starters.get(role), roster.filter(entry => entry.ruolo === role))}</select></label>`).join('')}${[0, 1, 2].map(index => `<label>Panchina ${index + 1}<select name="bench-${index}">${options(bench[index])}</select></label>`).join('')}<label>Capitano (×2)<select name="captain" required>${options(lineup.capitanoId)}</select></label><label>Vice-capitano<select name="vice" required>${options(lineup.viceCapitanoId)}</select></label></div>`;
    $('#formation-form button[type=submit]').classList.toggle('hidden', !lineup.targetMatchdayId);
    $('#edit-formation-button').classList.add('hidden');
}

async function refreshOpenFormation() {
    if (!state.activeTeam || !$('#formation-dialog').open) return;
    const [history, lineup] = await Promise.all([
        api(`/fanta-teams/${state.activeTeam.id}/formazioni`),
        api(`/fanta-teams/${state.activeTeam.id}/formazioni/lineup`)
    ]);
    state.formationHistory = history || [];
    state.currentLineup = lineup;
    renderFormationDialog();
}

function renderRosterHistory(history) {
    if (!history.length) return '<p class="empty-roster">Nessun risultato storico disponibile.</p>';
    const unit = isWorlds() ? 'pt' : 'pt medi';
    return `<h3>STORICO GIORNATE</h3>${history.map(item => {
        const day = state.matchdays.find(entry => entry.id === item.matchdayId);
        const badge = player => item.capitanoId === player.id ? '<span class="captain-badge">C</span>' : item.viceCapitanoId === player.id ? '<span class="captain-badge vice-badge">V</span>' : '';
        return `<article class="history-day"><header><strong>Giornata ${day?.numero ?? ''}</strong><span>${item.punteggioTotale == null ? 'In attesa' : `${Number(item.punteggioTotale).toFixed(1)} ${unit}`}${item.penaltyPoints ? ` · −${item.penaltyPoints} penalità` : ''}</span></header>${(item.players || []).map(player => `<div><span>${escapeHtml(player.role)}</span><strong>${escapeHtml(player.nickname)}${badge(player)}</strong><b class="${player.matchdayScore < 0 ? 'negative' : ''}">${player.matchdayScore == null ? 'In attesa' : `${Number(player.matchdayScore).toFixed(1)} pt`}</b></div>`).join('') || '<p>Nessuna formazione storica disponibile.</p>'}</article>`;
    }).join('')}`;
}

function openMatchday() {
    if (isWorlds()) {
        api('/matchdays', {method: 'POST', body: JSON.stringify({leagueId: state.leagueId})})
            .then(() => { toast('Calendario Worlds generato: 8 giornate'); return synchronizeLeaguePage(); })
            .catch(error => toast(error.message, true));
        return;
    }
    const form = $('#matchday-form');
    form.reset();
    form.elements.leagueId.value = state.leagueId;
    $('.form-error', form).textContent = '';
    $('#matchday-dialog').showModal();
}

// --------------------------------------------------------------------------- eventi
$('#league-navigation').addEventListener('click', event => {
    const button = event.target.closest('[data-section]');
    if (!button) return;
    setSection(button.dataset.section);
    if (button.dataset.section === 'market') refreshMarket();
});
$('#matchdays-list').addEventListener('click', async event => {
    const open = event.target.closest('[data-open-formation]');
    const confirm = event.target.closest('[data-confirm-formation]');
    const all = event.target.closest('[data-confirm-all-formations]');
    try {
        if (open) {
            await openFormation(open.dataset.openFormation);
            return;
        }
        if (confirm) {
            await api(`/fanta-teams/${state.activeTeam.id}/formazioni/${confirm.dataset.confirmFormation}/confirm`, {method: 'POST'});
            state.confirmedMatchdays.add(Number(confirm.dataset.confirmFormation));
            toast('Rosa confermata');
            renderMatchdays();
            return;
        }
        if (all) {
            const result = await api(`/admin/leagues/${state.leagueId}/matchdays/${all.dataset.confirmAllFormations}/formations/confirm-all`, {method: 'POST'});
            toast(`${result.confirmedTeams} squadre confermate`);
            state.confirmedMatchdays.add(Number(all.dataset.confirmAllFormations));
            renderMatchdays();
        }
    } catch (error) {
        toast(error.message, true);
    }
});
$('#logout-button').addEventListener('click', () => logout());
$('#create-matchday-button').addEventListener('click', openMatchday);
$('#open-formation-button').addEventListener('click', () => openFormation().catch(error => toast(error.message, true)));
$$('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
$('#auction-list').addEventListener('click', async event => {
    const start = event.target.closest('[data-start-auction]');
    const release = event.target.closest('[data-release]');
    try {
        if (start) state.activeAuction = await api('/auctions', {method: 'POST', body: JSON.stringify({leagueId: state.leagueId, lecPlayerId: Number(start.dataset.startAuction), fantaTeamId: state.activeTeam.id})});
        if (release) {
            await api(`/fanta-teams/${state.activeTeam.id}/rosa/${release.dataset.release}`, {method: 'DELETE'});
            toast('Player rilasciato: rimborso del 50%');
        }
        state.auctionRenderKey = null;
        await synchronizeLeaguePage();
    } catch (error) {
        toast(error.message, true);
    }
});
$('#auction-summary').addEventListener('input', event => {
    const input = event.target.closest('[name=credits]');
    if (!input) return;
    state.bidDraft = Number(input.value);
    const view = LeagueUtils.auctionViewState(state.activeAuction, state.activeTeam, state.bidDraft);
    const button = input.form?.querySelector('button[type=submit]');
    if (button) button.disabled = !view.canBid;
});
$('#auction-summary').addEventListener('submit', async event => {
    const form = event.target.closest('[data-bid]');
    if (!form) return;
    event.preventDefault();
    try {
        state.activeAuction = await api(`/auctions/${form.dataset.bid}/bids`, {method: 'POST', body: JSON.stringify({fantaTeamId: state.activeTeam.id, credits: state.bidDraft})});
        state.auctionRenderKey = null;
        renderAuction();
        await synchronizeLeaguePage();
    } catch (error) {
        toast(error.message, true);
    }
});
$('#auction-phase-controls').addEventListener('click', async event => {
    const button = event.target.closest('[data-auction-phase]');
    if (!button) return;
    try {
        const action = button.dataset.auctionPhase;
        await api(`/leagues/${state.leagueId}/auction/${action}`, {method: 'PUT'});
        state.auctionRenderKey = null;
        await synchronizeLeaguePage();
        toast(action === 'open' ? 'Asta della lega avviata' : 'Asta della lega terminata');
    } catch (error) {
        toast(error.message, true);
    }
});
$('#auto-complete-button').addEventListener('click', async () => {
    try {
        await api(`/leagues/${state.leagueId}/rosters/complete-randomly`, {method: 'POST'});
        toast('Rose completate casualmente rispettando i ruoli');
        await synchronizeLeaguePage();
    } catch (error) {
        toast(error.message, true);
    }
});
$('#market-role').addEventListener('change', event => { state.marketFilters.role = event.target.value; renderMarket(); });
$('#market-team').addEventListener('change', event => { state.marketFilters.team = event.target.value; renderMarket(); });
$('#market-sell').addEventListener('change', renderMarket);
$('#market-list').addEventListener('click', event => {
    const buy = event.target.closest('[data-buy]');
    const sell = event.target.closest('[data-sell]');
    if (buy) makeTransfer(Number(buy.dataset.buy), $('#market-sell').value ? Number($('#market-sell').value) : null);
    if (sell) makeTransfer(null, Number(sell.dataset.sell));
});
$('#formation-roles').addEventListener('change', () => { state.formationDirty = true; });
$('#match-selector').addEventListener('change', renderSelectedMatch);
$('#game-selector').addEventListener('change', renderSelectedGame);
$('#sync-button').addEventListener('click', async () => {
    if (state.user?.role !== 'ADMIN') return;
    const button = $('#sync-button');
    button.disabled = true;
    try {
        await CompetitionDataSource.synchronize(api, competition());
        toast('Sincronizzazione richiesta: lo scheduler la esegue entro pochi secondi');
        setTimeout(() => Promise.all([loadAdminDiagnostics(), renderExternalData()]).catch(renderAdminDiagnosticError), 20000);
    } catch (error) {
        renderAdminDiagnosticError(error);
    } finally {
        button.disabled = false;
    }
});
$('#correction-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (state.user?.role !== 'ADMIN') return;
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const correction = {participated: optionalBoolean(values.participated), kills: optionalNumber(values.kills), deaths: optionalNumber(values.deaths), assists: optionalNumber(values.assists), cs: optionalNumber(values.cs), visionScore: optionalNumber(values.visionScore), win: optionalBoolean(values.win)};
    try {
        await CompetitionDataSource.correctPlayerGame(api, values.gameId, values.playerId, correction);
        $('.form-error', form).textContent = '';
        toast('Correzione salvata');
        await renderExternalData();
    } catch (error) {
        $('.form-error', form).textContent = error.message;
    }
});
$('#restore-button').addEventListener('click', async () => {
    if (state.user?.role !== 'ADMIN') return;
    const form = $('#correction-form');
    const gameId = form.elements.gameId.value;
    const playerId = form.elements.playerId.value;
    if (!gameId || !playerId) {
        $('.form-error', form).textContent = 'Inserisci Game ID e Player ID per il ripristino.';
        return;
    }
    try {
        await CompetitionDataSource.restorePlayerGame(api, gameId, playerId);
        $('.form-error', form).textContent = '';
        toast('Dati provider ripristinati');
        await renderExternalData();
    } catch (error) {
        $('.form-error', form).textContent = error.message;
    }
});
$('#edit-formation-button').addEventListener('click', () => {
    state.formationEditing = true;
    state.formationDirty = false;
    renderFormationDialog();
});
$('#confirm-formation-button').addEventListener('click', async () => {
    if (!state.activeTeam || !state.activeFormationMatchdayId) return;
    const button = $('#confirm-formation-button');
    button.disabled = true;
    try {
        await api(`/fanta-teams/${state.activeTeam.id}/formazioni/${state.activeFormationMatchdayId}/confirm`, {method: 'POST'});
        state.confirmedMatchdays.add(Number(state.activeFormationMatchdayId));
        toast('Rosa confermata');
        renderFormationDialog();
        renderMatchdays();
    } catch (error) {
        button.disabled = false;
        toast(error.message, true);
    }
});
$('#formation-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const titolariIds = roles.map(role => Number(values[`role-${role}`]));
    try {
        if (isWorlds()) {
            const panchinaIds = [0, 1, 2].map(index => Number(values[`bench-${index}`])).filter(Boolean);
            const rolesById = Object.fromEntries(state.activeTeam.rosa.map(entry => [entry.lecPlayerId, entry.ruolo]));
            const errors = WorldsUi.validateLineup({starters: titolariIds, bench: panchinaIds, captainId: values.captain, viceId: values.vice, rolesById});
            if (errors.length) throw new Error(errors.join(' · '));
            state.currentLineup = await api(`/fanta-teams/${state.activeTeam.id}/formazioni/lineup`, {method: 'PUT', body: JSON.stringify({titolariIds, panchinaIds, capitanoId: Number(values.captain), viceCapitanoId: Number(values.vice)})});
            toast('Formazione Worlds salvata');
        } else {
            state.currentLineup = await LineupUi.saveLineup(api, state.activeTeam.id, titolariIds);
            toast(state.league.competition === 'LEC' ? 'Formazione salvata: sarà attiva da venerdì' : 'Formazione salvata');
        }
        state.formationEditing = false;
        state.formationDirty = false;
        $('.form-error', form).textContent = '';
        renderFormationDialog();
        await synchronizeLeaguePage();
    } catch (error) {
        $('.form-error', form).textContent = error.message;
    }
});
$('#matchday-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    try {
        const day = await api('/matchdays', {method: 'POST', body: JSON.stringify({leagueId: state.leagueId, numero: Number(values.numero), descrizione: values.descrizione, data: values.data || null})});
        $('#matchday-dialog').close();
        toast(`Giornata ${day.numero} creata: asta aperta`);
        state.auctionRenderKey = null;
        await synchronizeLeaguePage();
    } catch (error) {
        $('.form-error', form).textContent = error.message;
    }
});
window.addEventListener('beforeunload', () => {
    stopPageSynchronization();
    stopCumulativeRefresh();
    stopCountdown();
});
initialise();
