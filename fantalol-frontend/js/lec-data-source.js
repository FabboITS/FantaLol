window.LecDataSource={
    loadStandings(request){return request('/lec/standings')},
    loadPlayerPerformances(request){return request('/lec/performances')},
    loadCumulativePerformances(request){return request('/lec/cumulative-performances')},
    loadCumulativeRanking(request,leagueId){return request(`/leagues/${encodeURIComponent(leagueId)}/cumulative-ranking`)},
    loadMatches(request){return request('/lec/matches')},
    loadGame(request,matchId,gameId){return request(`/lec/matches/${encodeURIComponent(matchId)}/games/${encodeURIComponent(gameId)}`)},
    loadSynchronization(request){return request('/admin/lec/synchronization')},
    synchronize(request){return request('/admin/lec/synchronize',{method:'POST'})},
    correctPlayerGame(request,gameId,playerId,correction){return request(`/admin/lec/games/${encodeURIComponent(gameId)}/players/${encodeURIComponent(playerId)}`,{method:'PUT',body:JSON.stringify(correction)})},
    restorePlayerGame(request,gameId,playerId){return request(`/admin/lec/games/${encodeURIComponent(gameId)}/players/${encodeURIComponent(playerId)}/override`,{method:'DELETE'})}
};
