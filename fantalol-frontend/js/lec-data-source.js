function normalizeCumulativeSection(payload){if(Array.isArray(payload))return {status:'awaiting-data',lastUpdatedAt:null,provisional:true,items:payload};return {status:payload?.status||'awaiting-data',lastUpdatedAt:payload?.lastUpdatedAt||null,provisional:payload?.provisional??true,items:Array.isArray(payload?.items)?payload.items:[]}}
function cumulativeFreshnessLabel(section){if(section?.status==='stale')return `Dati provvisori · ultimo aggiornamento ${section.lastUpdatedAt?new Date(section.lastUpdatedAt).toLocaleString('it-IT'):'non disponibile'}`;if(section?.status!=='fresh'||!section.lastUpdatedAt)return 'In attesa della prima sincronizzazione';return `Aggiornato ${new Date(section.lastUpdatedAt).toLocaleString('it-IT')}`}
window.LecDataSource={
    loadStandings(request){return request('/lec/standings')},
    loadPlayerPerformances(request){return request('/lec/performances')},
    async loadCumulativePerformances(request){return normalizeCumulativeSection(await request('/lec/cumulative-performances'))},
    async loadCumulativeRanking(request,leagueId){return normalizeCumulativeSection(await request(`/leagues/${encodeURIComponent(leagueId)}/cumulative-ranking`))},
    cumulativeFreshnessLabel,
    loadMatches(request){return request('/lec/matches')},
    loadGame(request,matchId,gameId){return request(`/lec/matches/${encodeURIComponent(matchId)}/games/${encodeURIComponent(gameId)}`)},
    loadSynchronization(request){return request('/admin/lec/synchronization')},
    synchronize(request){return request('/admin/lec/synchronize',{method:'POST'})},
    correctPlayerGame(request,gameId,playerId,correction){return request(`/admin/lec/games/${encodeURIComponent(gameId)}/players/${encodeURIComponent(playerId)}`,{method:'PUT',body:JSON.stringify(correction)})},
    restorePlayerGame(request,gameId,playerId){return request(`/admin/lec/games/${encodeURIComponent(gameId)}/players/${encodeURIComponent(playerId)}/override`,{method:'DELETE'})}
};
