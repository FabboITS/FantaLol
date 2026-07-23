import { demoFantasyTeams, demoLeague, demoMatchdays, demoPlayers } from '../data/demoData';

const STORE_KEY = 'fantalol_react_demo';
const wait = (value, delay = 180) => new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), delay));

function initialState() {
  return {
    users: [
      { username: 'demo', email: 'demo@fantalol.local', password: 'demo123', role: 'USER' },
      { username: 'admin', email: 'admin@fantalol.local', password: 'admin123', role: 'ADMIN' },
    ],
    players: demoPlayers,
    leagues: [demoLeague],
    fantasyTeams: demoFantasyTeams,
    matchdays: demoMatchdays,
  };
}

function readStore() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) || initialState();
  } catch {
    return initialState();
  }
}

function writeStore(data) {
  localStorage.setItem(STORE_KEY, JSON.stringify(data));
}

export const demoApi = {
  async login({ username, password }) {
    const user = readStore().users.find((item) => item.username === username && item.password === password);
    if (!user) throw new Error('Incorrect username or password. Try demo / demo123.');
    return wait({ token: `demo-token-${user.username}`, username: user.username, role: user.role });
  },

  async register({ username, email, password }) {
    const store = readStore();
    if (store.users.some((item) => item.username.toLowerCase() === username.toLowerCase())) {
      throw new Error('This username is already in use.');
    }
    store.users.push({ username, email, password, role: 'USER' });
    writeStore(store);
    return wait({ username, email, role: 'USER' });
  },

  async getPlayers() {
    return wait(readStore().players);
  },

  async getLeagues(username) {
    const store = readStore();
    if (!username) return wait([]);
    const memberships = new Set(
      store.fantasyTeams.filter((team) => team.ownerUsername === username).map((team) => team.leagueId),
    );
    return wait(store.leagues.filter((league) => league.adminUsername === username || memberships.has(league.id)));
  },

  async getLeague(id) {
    const league = readStore().leagues.find((item) => item.id === Number(id));
    if (!league) throw new Error('League not found.');
    return wait(league);
  },

  async getFantasyTeams(leagueId) {
    return wait(readStore().fantasyTeams.filter((team) => team.leagueId === Number(leagueId)));
  },

  async getMatchdays(leagueId) {
    return wait(readStore().matchdays.filter((day) => day.leagueId === Number(leagueId)));
  },

  async createLeague(username, values) {
    const store = readStore();
    const id = Math.max(0, ...store.leagues.map((item) => item.id)) + 1;
    const league = {
      id,
      nome: values.nome,
      codiceInvito: Math.random().toString(36).slice(2, 8).toUpperCase(),
      creditiIniziali: Number(values.creditiIniziali),
      adminUsername: username,
      numeroSquadre: 0,
      participantCount: null,
      auctionOpen: false,
      maxRosterSize: 10,
      maxPerRole: 2,
    };
    store.leagues.push(league);
    writeStore(store);
    return wait(league);
  },

  async joinLeague(username, values) {
    const store = readStore();
    const league = store.leagues.find(
      (item) => item.codiceInvito.toLowerCase() === values.codiceInvito.trim().toLowerCase(),
    );
    if (!league) throw new Error('No league matches that invitation code.');
    if (store.fantasyTeams.some((team) => team.leagueId === league.id && team.ownerUsername === username)) {
      throw new Error('You already have a team in this league.');
    }
    const id = Math.max(0, ...store.fantasyTeams.map((item) => item.id)) + 1;
    store.fantasyTeams.push({
      id,
      leagueId: league.id,
      nome: values.nomeSquadra,
      ownerUsername: username,
      creditiResidui: league.creditiIniziali,
      punti: 0,
      rosa: [],
    });
    league.numeroSquadre += 1;
    writeStore(store);
    return wait(league);
  },

  reset() {
    localStorage.removeItem(STORE_KEY);
  },
};
