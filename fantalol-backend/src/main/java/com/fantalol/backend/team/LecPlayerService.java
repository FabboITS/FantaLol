package com.fantalol.backend.team;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.team.dto.LecPlayerRequest;
import com.fantalol.backend.team.dto.LecPlayerResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class LecPlayerService {

    private final LecPlayerRepository lecPlayerRepository;
    private final LecTeamRepository lecTeamRepository;

    @Transactional(readOnly = true)
    public List<LecPlayerResponse> findAll(PlayerRole ruolo, Long teamId) {
        List<LecPlayer> players;
        if (ruolo != null) {
            players = lecPlayerRepository.findByRuolo(ruolo);
        } else if (teamId != null) {
            players = lecPlayerRepository.findByTeamId(teamId);
        } else {
            players = lecPlayerRepository.findAll();
        }
        return players.stream().map(LecPlayerResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public LecPlayerResponse findById(Long id) {
        return LecPlayerResponse.from(getOrThrow(id));
    }

    @Transactional
    public LecPlayerResponse create(LecPlayerRequest request) {
        LecTeam team = lecTeamRepository.findById(request.teamId())
                .orElseThrow(() -> new ResourceNotFoundException("Team LEC non trovato con id: " + request.teamId()));

        LecPlayer player = LecPlayer.builder()
                .nickname(request.nickname())
                .nomeReale(request.nomeReale())
                .nazionalita(request.nazionalita())
                .ruolo(request.ruolo())
                .quotazione(request.quotazione())
                .team(team)
                .build();

        return LecPlayerResponse.from(lecPlayerRepository.save(player));
    }

    @Transactional
    public LecPlayerResponse update(Long id, LecPlayerRequest request) {
        LecPlayer player = getOrThrow(id);
        LecTeam team = lecTeamRepository.findById(request.teamId())
                .orElseThrow(() -> new ResourceNotFoundException("Team LEC non trovato con id: " + request.teamId()));

        player.setNickname(request.nickname());
        player.setNomeReale(request.nomeReale());
        player.setNazionalita(request.nazionalita());
        player.setRuolo(request.ruolo());
        player.setQuotazione(request.quotazione());
        player.setTeam(team);

        return LecPlayerResponse.from(lecPlayerRepository.save(player));
    }

    @Transactional
    public void delete(Long id) {
        lecPlayerRepository.delete(getOrThrow(id));
    }

    LecPlayer getOrThrow(Long id) {
        return lecPlayerRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + id));
    }
}
