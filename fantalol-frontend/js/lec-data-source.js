window.LecDataSource={
    loadStandings(request){return request('/lec/standings')},
    loadPlayerPerformances(request){return request('/lec/performances')},
    loadMatches(request){return request('/lec/matches')},
    loadGame(request,matchId,gameId){return request(`/lec/matches/${encodeURIComponent(matchId)}/games/${encodeURIComponent(gameId)}`)}
};
