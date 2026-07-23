export const demoPlayers = [
  { id: 1, nickname: 'BrokenBlade', ruolo: 'TOP', teamNome: 'G2 Esports', teamSigla: 'G2', nazionalita: 'Germany', quotazione: 85, color: '#f97316', imageUrl: '/Player_immage/Top/BrokenBlade.jpg' },
  { id: 2, nickname: 'Yike', ruolo: 'JUNGLE', teamNome: 'Karmine Corp', teamSigla: 'KC', nazionalita: 'Denmark', quotazione: 80, color: '#2563eb', imageUrl: '/Player_immage/Jungle/Yike.jpg' },
  { id: 3, nickname: 'Caps', ruolo: 'MID', teamNome: 'G2 Esports', teamSigla: 'G2', nazionalita: 'Denmark', quotazione: 100, color: '#f97316', imageUrl: '/Player_immage/Mid/Caps.jpg' },
  { id: 4, nickname: 'Caliste', ruolo: 'ADC', teamNome: 'Karmine Corp', teamSigla: 'KC', nazionalita: 'France', quotazione: 85, color: '#2563eb', imageUrl: '/Player_immage/Adc/Caliste.jpg' },
  { id: 5, nickname: 'Labrov', ruolo: 'SUPPORT', teamNome: 'G2 Esports', teamSigla: 'G2', nazionalita: 'Greece', quotazione: 80, color: '#f97316', imageUrl: '/Player_immage/Support/Labrov.jpg' },
  { id: 6, nickname: 'Canna', ruolo: 'TOP', teamNome: 'Karmine Corp', teamSigla: 'KC', nazionalita: 'South Korea', quotazione: 90, color: '#2563eb', imageUrl: '/Player_immage/Top/Canna.jpg' },
  { id: 7, nickname: 'Elyoya', ruolo: 'JUNGLE', teamNome: 'Movistar KOI', teamSigla: 'MKOI', nazionalita: 'Spain', quotazione: 95, color: '#a855f7', imageUrl: '/Player_immage/Jungle/Elyoya.jpg' },
  { id: 8, nickname: 'Humanoid', ruolo: 'MID', teamNome: 'Team Vitality', teamSigla: 'VIT', nazionalita: 'Czech Republic', quotazione: 75, color: '#eab308', imageUrl: '/Player_immage/Mid/Humanoid.jpg' },
  { id: 9, nickname: 'Upset', ruolo: 'ADC', teamNome: 'Fnatic', teamSigla: 'FNC', nazionalita: 'Germany', quotazione: 80, color: '#ef4444', imageUrl: '/Player_immage/Adc/Upset.jpg' },
  { id: 10, nickname: 'Mikyx', ruolo: 'SUPPORT', teamNome: 'SK Gaming', teamSigla: 'SK', nazionalita: 'Slovenia', quotazione: 75, color: '#22c55e', imageUrl: '/Player_immage/Support/Mikyx.jpg' },
];

export const demoLeague = {
  id: 1,
  nome: 'Rift Rivals',
  codiceInvito: 'RIFT26',
  creditiIniziali: 1000,
  adminUsername: 'demo',
  numeroSquadre: 4,
  participantCount: 4,
  auctionOpen: true,
  maxRosterSize: 10,
  maxPerRole: 2,
};

export const demoFantasyTeams = [
  {
    id: 1,
    leagueId: 1,
    nome: 'Neon Dragons',
    ownerUsername: 'demo',
    creditiResidui: 580,
    punti: 48.6,
    rosa: demoPlayers.slice(0, 5).map((player, index) => ({
      id: index + 1,
      lecPlayerId: player.id,
      lecPlayerNickname: player.nickname,
      ruolo: player.ruolo,
      creditiSpesi: player.quotazione,
    })),
  },
  { id: 2, leagueId: 1, nome: 'Baron Bandits', ownerUsername: 'ahri_main', creditiResidui: 610, punti: 44.2, rosa: [] },
  { id: 3, leagueId: 1, nome: 'Nexus Knights', ownerUsername: 'jungler99', creditiResidui: 545, punti: 41.8, rosa: [] },
  { id: 4, leagueId: 1, nome: 'Pixel Pentakill', ownerUsername: 'lulu', creditiResidui: 660, punti: 39.1, rosa: [] },
];

export const demoMatchdays = [
  { id: 1, leagueId: 1, numero: 1, descrizione: 'Opening week', data: '2026-07-18', chiusa: true, status: 'CLOSED' },
  { id: 2, leagueId: 1, numero: 2, descrizione: 'Summer split', data: '2026-07-25', chiusa: false, status: 'OPEN', auctionLocked: true },
];

export const roleColors = {
  TOP: '#f97316',
  JUNGLE: '#22c55e',
  MID: '#8b5cf6',
  ADC: '#3b82f6',
  SUPPORT: '#ec4899',
};
