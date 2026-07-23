import { demoApi } from './demoApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '');
export const isDemoMode = !API_BASE_URL;

async function request(path, options = {}) {
  const token = localStorage.getItem('fantalol_react_token');
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.message || `Request failed (${response.status})`);
  return body;
}

export const api = {
  login: (values) => (isDemoMode ? demoApi.login(values) : request('/api/auth/login', { method: 'POST', body: JSON.stringify(values) })),
  register: (values) => (isDemoMode ? demoApi.register(values) : request('/api/auth/register', { method: 'POST', body: JSON.stringify(values) })),
  getPlayers: () => (isDemoMode ? demoApi.getPlayers() : request('/api/players')),
  getLeagues: (username) => (isDemoMode ? demoApi.getLeagues(username) : request('/api/leagues')),
  getLeague: async (id, username) => {
    if (isDemoMode) return demoApi.getLeague(id);
    const leagues = await api.getLeagues(username);
    const league = leagues.find((item) => Number(item.id) === Number(id));
    if (!league) throw new Error('League not found or inaccessible.');
    return league;
  },
  getFantasyTeams: (id) => (isDemoMode ? demoApi.getFantasyTeams(id) : request(`/api/fanta-teams/by-league/${id}`)),
  getMatchdays: async (id) => {
    if (isDemoMode) return demoApi.getMatchdays(id);
    const days = await request('/api/matchdays');
    return days.filter((day) => Number(day.leagueId) === Number(id));
  },
  createLeague: (username, values) => (isDemoMode
    ? demoApi.createLeague(username, values)
    : request('/api/leagues', { method: 'POST', body: JSON.stringify(values) })),
  joinLeague: (username, values) => (isDemoMode
    ? demoApi.joinLeague(username, values)
    : request('/api/fanta-teams/join', { method: 'POST', body: JSON.stringify(values) })),
  resetDemo: demoApi.reset,
};
