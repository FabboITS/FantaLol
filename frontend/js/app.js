const state = {
    token: localStorage.getItem('fantalol_token'),
    user: JSON.parse(localStorage.getItem('fantalol_user') || 'null'),
    competition: CompetitionState.read(localStorage),
    players: [],
    teams: [],
    edition: null,
    mine: [],
    leagues: [],
    role: '',
    query: '',
    matchState: 'upcoming',
    feed: null,
    leagueCompetition: CompetitionState.read(localStorage),
    editions: []
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'}[char]));

async function api(path, options = {}) {
    const headers = {'Content-Type': 'application/json', ...options.headers};
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    const response = await fetch(`/api${path}`, {...options, headers});
    if (response.status === 204) return null;
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        if (response.status === 401 && state.token) logout(false);
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

// --------------------------------------------------------------------------- sessione
function setSession(auth) {
    state.token = auth.token;
    state.user = {username: auth.username, role: auth.role};
    localStorage.setItem('fantalol_token', auth.token);
    localStorage.setItem('fantalol_user', JSON.stringify(state.user));
    renderSession();
    loadPrivateData();
}

function logout(notify = true) {
    state.token = null;
    state.user = null;
    localStorage.removeItem('fantalol_token');
    localStorage.removeItem('fantalol_user');
    renderSession();
    if (notify) toast('Sessione terminata');
}

function renderSession() {
    const logged = Boolean(state.token);
    $('#auth-button').classList.toggle('hidden', logged);
    $('#logout-button').classList.toggle('hidden', !logged);
    $('#user-chip').classList.toggle('hidden', !logged);
    $('#league-guest').classList.toggle('hidden', logged);
    $('#league-dashboard').classList.toggle('hidden', !logged);
    if (logged) $('#user-chip').textContent = `${state.user.username} · ${state.user.role}`;
}

// --------------------------------------------------------------------------- competizione
function renderCompetitionChips() {
    for (const selector of ['#home-competitions', '#players-competitions', '#matches-competitions']) {
        $(selector).innerHTML = CompetitionState.chipsHtml(state.competition);
    }
    $('#team-count-label').textContent = `Team ${state.competition}`;
}

function selectCompetition(code) {
    state.competition = CompetitionState.write(localStorage, code);
    renderCompetitionChips();
    loadPublicData();
    loadMatches();
}

// --------------------------------------------------------------------------- players
async function loadPublicData() {
    const competition = state.competition;
    $('#players-grid').innerHTML = '<p class="loading">Caricamento roster…</p>';
    try {
        const [players, teams] = await Promise.all([
            CompetitionDataSource.loadPlayers(api, competition),
            CompetitionDataSource.loadTeams(api, competition)
        ]);
        if (competition !== state.competition) return;
        state.players = players;
        state.teams = teams;
        $('#player-count').textContent = players.length;
        $('#team-count').textContent = teams.length;
        renderPlayers();
    } catch (error) {
        $('#players-grid').innerHTML = '<p class="empty-grid">Backend non raggiungibile. Avvia il server Django e ricarica la pagina.</p>';
        toast(error.message, true);
    }
}

function portrait(player) {
    const fallback = `<span class="initials" style="background:${PlayersView.avatarColor(player.nickname)}">${escapeHtml(PlayersView.initials(player.nickname))}</span>`;
    const image = player.imageUrl ? `<img class="player-portrait" src="${escapeHtml(player.imageUrl)}" alt="Ritratto di ${escapeHtml(player.nickname)}" loading="lazy">` : '';
    return `<div class="avatar">${fallback}${image}</div>`;
}

function teamLogo(team) {
    const fallback = `<span class="team-initials" style="background:${PlayersView.avatarColor(team.nome)}">${escapeHtml(PlayersView.initials(team.sigla || team.nome))}</span>`;
    const image = team.logoUrl ? `<img class="team-logo-large" src="${escapeHtml(team.logoUrl)}" alt="" aria-hidden="true" loading="lazy">` : '';
    return `<div class="team-logo-wrap">${fallback}${image}</div>`;
}

function renderPlayerCard(player) {
    return `<article class="scout-card"><span class="role-mark">${escapeHtml(player.ruolo[0])}</span><span class="role">${escapeHtml(player.ruolo)}</span>${portrait(player)}<h3>${escapeHtml(player.nickname)}</h3><p class="team"><span>${escapeHtml(player.teamSigla || player.teamNome)} · ${escapeHtml(player.nazionalita || player.competition)}</span></p><div class="card-footer"><span>Quotazione</span><strong>${player.quotazione} CR</strong></div></article>`;
}

function renderPlayers() {
    const groups = PlayersView.groupByTeam(state.teams, state.players, {role: state.role, query: state.query});
    const edition = state.teams[0]?.competition ? `${state.teams.length} team · ${state.players.length} player · ${state.competition}` : '';
    $('#players-edition').textContent = edition;
    $('#players-grid').innerHTML = groups.length
        ? groups.map(({team, players}) => `<section class="team-roster"><header class="team-roster-head">${teamLogo(team)}<div><h3>${escapeHtml(team.nome)}</h3><span>${escapeHtml(team.sigla || '')}</span></div></header><div class="players-grid">${players.map(renderPlayerCard).join('')}</div></section>`).join('')
        : `<p class="empty-grid">${state.players.length ? 'Nessun player corrisponde ai filtri.' : `Nessun roster ${escapeHtml(state.competition)} disponibile: in attesa della sincronizzazione.`}</p>`;
}

// --------------------------------------------------------------------------- partite
async function loadMatches() {
    $('#matches-list').innerHTML = '<p class="loading">Caricamento partite…</p>';
    try {
        const feed = await CompetitionDataSource.loadFeed(api, state.competition, state.matchState, 50);
        state.feed = feed;
        renderMatches();
        if (state.matchState === 'upcoming') $('#match-count').textContent = feed.items.length;
    } catch (error) {
        $('#matches-list').innerHTML = `<p class="empty-grid">${escapeHtml(error.message)}</p>`;
    }
}

function renderMatches() {
    const feed = state.feed;
    const fresh = MatchesView.freshness(feed);
    const label = $('#matches-freshness');
    label.textContent = fresh.label;
    label.classList.toggle('stale', fresh.stale);
    $('#matches-list').innerHTML = feed.items.length ? feed.items.map(match => {
        const when = match.beginAt ? new Date(match.beginAt).toLocaleString('it-IT', {weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'}) : 'Data da definire';
        const teams = match.teams.map(team => `<div class="match-team ${team.winner ? 'winner' : ''}">${team.logoUrl ? `<img src="${escapeHtml(team.logoUrl)}" alt="" loading="lazy">` : `<span class="team-initials small" style="background:${PlayersView.avatarColor(team.name)}">${escapeHtml(PlayersView.initials(team.acronym || team.name))}</span>`}<strong>${escapeHtml(team.acronym || team.name)}</strong>${match.status === 'not_started' ? '' : `<b>${team.score}</b>`}</div>`).join('<span class="versus">vs</span>');
        const action = match.hasStats ? `<button class="button button-ghost" data-open-match="${match.id}">Box score</button>` : `<span class="match-status">${escapeHtml(MatchesView.statusLabel(match))}</span>`;
        return `<article class="match-card ${match.status}"><div class="match-meta"><span class="competition-tag">${escapeHtml(match.competition || '')}${match.stage ? ` · ${escapeHtml(match.stage)}` : ''}</span><time>${escapeHtml(when)}</time></div><div class="match-teams">${teams}</div>${action}</article>`;
    }).join('') : '<p class="empty-grid">Nessuna partita in questa sezione.</p>';
}

async function openMatchDrawer(matchId) {
    const drawer = $('#match-drawer');
    const match = state.feed?.items.find(item => Number(item.id) === Number(matchId));
    $('#match-drawer-title').textContent = match ? MatchesView.scoreLine(match) : 'PARTITA';
    $('#match-drawer-games').innerHTML = '<p class="loading">Caricamento statistiche…</p>';
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    try {
        const payload = await CompetitionDataSource.loadMatchGames(api, matchId);
        $('#match-drawer-attribution').textContent = MatchesView.attribution(payload);
        $('#match-drawer-games').innerHTML = payload.items.length ? payload.items.map(game => `<section class="drawer-game"><h3>Game ${game.gameNumber}${game.mvp ? ` · MVP ${escapeHtml(game.mvp)}` : ''}</h3>${MatchesView.groupPlayersByTeam(game.players).map(group => `<div class="game-team"><h4>${escapeHtml(group.team)}</h4>${group.players.map(player => `<div class="box-row"><img src="${escapeHtml(player.championImagePath)}" alt="${escapeHtml(player.championName)}" loading="lazy"><strong>${escapeHtml(player.nickname)}</strong><span>${escapeHtml(player.role)}</span><b>${player.kills}/${player.deaths}/${player.assists}</b><span>${player.role === 'SUPPORT' ? `Vision ${player.visionScore}` : `${player.cs} CS`}</span><em>KDA ${MatchesView.kdaLabel(player)}</em><b class="game-fantasy-score">${player.fantasyScore == null ? 'In attesa' : `${Number(player.fantasyScore).toFixed(2)} pt`}</b></div>`).join('')}</div>`).join('')}</section>`).join('') : '<p class="empty-list">Statistiche non ancora disponibili su Leaguepedia.</p>';
    } catch (error) {
        $('#match-drawer-games').innerHTML = `<p class="empty-list">${escapeHtml(error.message)}</p>`;
    }
}

function closeMatchDrawer() {
    $('#match-drawer').classList.remove('open');
    $('#match-drawer').setAttribute('aria-hidden', 'true');
}

// --------------------------------------------------------------------------- leghe
async function loadPrivateData() {
    if (!state.token) return;
    try {
        const [mine, leagues] = await Promise.all([api('/fanta-teams/me'), api('/leagues')]);
        state.mine = mine;
        state.leagues = leagues;
        renderLeagues(leagues);
    } catch (error) {
        toast(error.message, true);
    }
}

function canDeleteLeague(league) {
    return state.user?.role === 'ADMIN' || league.adminUsername === state.user?.username;
}

function renderLeagueCard(league) {
    const deleteButton = canDeleteLeague(league) ? `<button class="league-delete" type="button" data-delete-league="${league.id}">Elimina</button>` : '';
    const credits = league.ruleset === 'WORLDS' ? `budget ${league.creditiIniziali}` : `${league.creditiIniziali} crediti`;
    return `<article class="league-panel"><a class="league-launcher" href="/lega.html?id=${league.id}"><span class="competition-tag">${escapeHtml(league.competition)} · ${escapeHtml(league.editionName || '')}</span><p class="panel-meta">${league.numeroSquadre} squadre · ${credits} · admin ${escapeHtml(league.adminUsername)}</p><h3>${escapeHtml(league.nome)}</h3><p>Codice invito</p><div class="invite-code">${escapeHtml(league.codiceInvito)}</div><span class="league-open">Apri lega →</span></a>${deleteButton}</article>`;
}

function renderLeagues(items) {
    $('#leagues-list').innerHTML = items.length ? items.map(renderLeagueCard).join('') : '<div class="empty-state"><h3>Nessuna lega</h3><p>Crea una lega o entra con un codice invito.</p></div>';
}

async function loadEditions(code) {
    state.leagueCompetition = CompetitionState.normalize(code);
    $('#league-competitions').innerHTML = CompetitionState.chipsHtml(state.leagueCompetition, 'data-league-competition');
    const worlds = CompetitionState.isWorlds(state.leagueCompetition);
    $('#worlds-summary').classList.toggle('hidden', !worlds);
    $('#credits-field').classList.toggle('hidden', worlds);
    $('#worlds-summary-list').innerHTML = WorldsUi.RULES_SUMMARY.map(rule => `<li>${escapeHtml(rule)}</li>`).join('');
    const select = $('#league-edition');
    select.innerHTML = '<option value="">Caricamento…</option>';
    try {
        state.editions = await CompetitionDataSource.loadEditions(api, state.leagueCompetition);
        select.innerHTML = state.editions.length
            ? state.editions.map(edition => `<option value="${edition.id}">${escapeHtml(edition.name)}${edition.isActive ? '' : ' (futura)'}</option>`).join('')
            : '<option value="">Nessuna edizione attiva o futura</option>';
    } catch (error) {
        select.innerHTML = '<option value="">Edizioni non disponibili</option>';
    }
}

function openAuth() {
    if (state.token) {
        location.hash = 'leagues';
        return;
    }
    $('#auth-dialog').showModal();
}

function setAuthMode(mode) {
    const register = mode === 'register';
    $$('[data-auth-tab]').forEach(button => button.classList.toggle('active', button.dataset.authTab === mode));
    $('#email-field').classList.toggle('hidden', !register);
    $('#email-field input').required = register;
    $('#auth-title').textContent = register ? 'CREA ACCOUNT' : 'ACCEDI';
    $('#auth-form').dataset.mode = mode;
    $('#auth-form [type=password]').autocomplete = register ? 'new-password' : 'current-password';
    $('.form-error', $('#auth-form')).textContent = '';
}

function openLeague(mode) {
    if (!state.token) {
        openAuth();
        return;
    }
    const join = mode === 'join';
    $('#create-fields').classList.toggle('hidden', join);
    $('#join-fields').classList.toggle('hidden', !join);
    $('#league-modal-title').textContent = join ? 'ENTRA IN LEGA' : 'CREA LEGA';
    $('#league-kicker').textContent = join ? 'Hai un codice?' : 'Nuova competizione';
    $('#league-form').dataset.mode = mode;
    if (!join) loadEditions(state.competition);
    $('#league-dialog').showModal();
}

function setRulesTab(tab) {
    $$('[data-rules-tab]').forEach(button => button.classList.toggle('active', button.dataset.rulesTab === tab));
    $$('[data-rules]').forEach(section => section.classList.toggle('hidden', section.dataset.rules !== tab));
}

function isEditableTarget(target) {
    return target instanceof Element && (target.matches('input,textarea,select') || target.isContentEditable);
}

function isAdminDirectoryShortcut(event) {
    const yKey = event.code === 'KeyY' || event.key.toLowerCase() === 'y';
    return event.ctrlKey && !event.altKey && !event.metaKey && yKey;
}

async function openUserDirectory() {
    if (state.user?.role !== 'ADMIN' || !state.token) return;
    const dialog = $('#user-directory-dialog');
    const count = $('#user-directory-count');
    const list = $('#user-directory-list');
    count.textContent = '';
    list.innerHTML = '<p class="directory-loading">Caricamento utenti…</p>';
    try {
        const users = await api('/users');
        count.textContent = `${users.length} ${users.length === 1 ? 'utente registrato' : 'utenti registrati'}`;
        list.innerHTML = users.length ? users.map(user => `<div class="directory-user"><strong>${escapeHtml(user.username)}</strong><span>${escapeHtml(user.email)}</span></div>`).join('') : '<p class="directory-empty">Nessun utente regolare registrato.</p>';
        dialog.showModal();
    } catch (error) {
        toast(error.message, true);
    }
}

async function deleteLeague(league) {
    if (!confirm(`Eliminare definitivamente la lega “${league.nome}”?`)) return;
    try {
        await api(`/leagues/${league.id}`, {method: 'DELETE'});
        toast('Lega eliminata');
        await loadPrivateData();
    } catch (error) {
        toast(error.message, true);
    }
}

// --------------------------------------------------------------------------- eventi
$('#auth-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const mode = form.dataset.mode || 'login';
    const values = Object.fromEntries(new FormData(form));
    const error = $('.form-error', form);
    error.textContent = '';
    try {
        if (mode === 'register') {
            await api('/auth/register', {method: 'POST', body: JSON.stringify(values)});
            toast('Account creato. Ora puoi accedere.');
            setAuthMode('login');
            return;
        }
        const auth = await api('/auth/login', {method: 'POST', body: JSON.stringify({username: values.username, password: values.password})});
        setSession(auth);
        $('#auth-dialog').close();
        form.reset();
        toast(`Bentornato, ${auth.username}`);
    } catch (err) {
        error.textContent = err.message;
    }
});

$('#league-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const error = $('.form-error', form);
    try {
        if (form.dataset.mode === 'join') {
            await api('/fanta-teams/join', {method: 'POST', body: JSON.stringify({codiceInvito: values.codiceInvito, nomeSquadra: values.nomeSquadra})});
        } else {
            const body = {nome: values.nome, competition: state.leagueCompetition, editionId: values.editionId ? Number(values.editionId) : null};
            if (!CompetitionState.isWorlds(state.leagueCompetition)) body.creditiIniziali = Number(values.creditiIniziali);
            await api('/leagues', {method: 'POST', body: JSON.stringify(body)});
        }
        $('#league-dialog').close();
        form.reset();
        toast(form.dataset.mode === 'join' ? 'Squadra iscritta alla lega' : 'Lega creata');
        loadPrivateData();
    } catch (err) {
        error.textContent = err.message;
    }
});

document.addEventListener('click', event => {
    const chip = event.target.closest('[data-competition]');
    if (chip) selectCompetition(chip.dataset.competition);
    const leagueChip = event.target.closest('[data-league-competition]');
    if (leagueChip) loadEditions(leagueChip.dataset.leagueCompetition);
});
$$('[data-auth-action]').forEach(button => button.addEventListener('click', openAuth));
$('#auth-button').addEventListener('click', openAuth);
$('#logout-button').addEventListener('click', () => logout());
$$('[data-auth-tab]').forEach(button => button.addEventListener('click', () => setAuthMode(button.dataset.authTab)));
$$('[data-rules-tab]').forEach(button => button.addEventListener('click', () => setRulesTab(button.dataset.rulesTab)));
$('#create-league-button').addEventListener('click', () => openLeague('create'));
$('#join-league-button').addEventListener('click', () => openLeague('join'));
$('#leagues-list').addEventListener('click', event => {
    const button = event.target.closest('[data-delete-league]');
    if (!button) return;
    const league = state.leagues.find(item => item.id === Number(button.dataset.deleteLeague));
    if (league) deleteLeague(league);
});
$('#rules-button').addEventListener('click', () => $('#rules-dialog').showModal());
$$('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
$('#role-filters').addEventListener('click', event => {
    const button = event.target.closest('[data-role]');
    if (!button) return;
    state.role = button.dataset.role;
    $$('[data-role]').forEach(filter => filter.classList.toggle('active', filter === button));
    renderPlayers();
});
$('#player-search').addEventListener('input', event => {
    state.query = event.target.value;
    renderPlayers();
});
$('#players-grid').addEventListener('error', event => {
    if (event.target.matches('.player-portrait,.team-logo-large')) event.target.hidden = true;
}, true);
$('#matches-list').addEventListener('error', event => {
    if (event.target.matches('img')) event.target.hidden = true;
}, true);
$('#match-tabs').addEventListener('click', event => {
    const tab = event.target.closest('[data-match-state]');
    if (!tab) return;
    state.matchState = tab.dataset.matchState;
    $$('[data-match-state]').forEach(item => item.classList.toggle('active', item === tab));
    loadMatches();
});
$('#matches-list').addEventListener('click', event => {
    const open = event.target.closest('[data-open-match]');
    if (open) openMatchDrawer(open.dataset.openMatch);
});
$('#match-drawer-close').addEventListener('click', closeMatchDrawer);
$('#match-drawer').addEventListener('click', event => {
    if (event.target.id === 'match-drawer') closeMatchDrawer();
});
$$('.site-header nav a').forEach(link => link.addEventListener('click', () => {
    $$('.site-header nav a').forEach(item => item.classList.remove('active'));
    link.classList.add('active');
}));
document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeMatchDrawer();
    if (!isAdminDirectoryShortcut(event)) return;
    if (state.user?.role !== 'ADMIN' || isEditableTarget(event.target)) return;
    event.preventDefault();
    openUserDirectory();
});

renderSession();
setAuthMode('login');
renderCompetitionChips();
loadPublicData();
loadMatches();
if (state.token) loadPrivateData();
if (new URLSearchParams(location.search).get('login') === '1') openAuth();
