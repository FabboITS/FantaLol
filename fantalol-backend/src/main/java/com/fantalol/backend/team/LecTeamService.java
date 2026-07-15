package com.fantalol.backend.team;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.team.dto.LecTeamRequest;
import com.fantalol.backend.team.dto.LecTeamResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class LecTeamService {

    private final LecTeamRepository lecTeamRepository;

    @Transactional(readOnly = true)
    public List<LecTeamResponse> findAll() {
        return lecTeamRepository.findAll().stream().map(LecTeamResponse::summaryFrom).toList();
    }

    @Transactional(readOnly = true)
    public LecTeamResponse findById(Long id) {
        return LecTeamResponse.from(getOrThrow(id));
    }

    @Transactional
    public LecTeamResponse create(LecTeamRequest request) {
        if (lecTeamRepository.existsByNomeIgnoreCase(request.nome())) {
            throw new BusinessRuleException("Esiste già un team LEC con nome: " + request.nome());
        }
        LecTeam team = LecTeam.builder()
                .nome(request.nome())
                .sigla(request.sigla())
                .logoUrl(request.logoUrl())
                .build();
        return LecTeamResponse.summaryFrom(lecTeamRepository.save(team));
    }

    @Transactional
    public LecTeamResponse update(Long id, LecTeamRequest request) {
        LecTeam team = getOrThrow(id);
        team.setNome(request.nome());
        team.setSigla(request.sigla());
        team.setLogoUrl(request.logoUrl());
        return LecTeamResponse.summaryFrom(lecTeamRepository.save(team));
    }

    @Transactional
    public void delete(Long id) {
        LecTeam team = getOrThrow(id);
        lecTeamRepository.delete(team);
    }

    LecTeam getOrThrow(Long id) {
        return lecTeamRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Team LEC non trovato con id: " + id));
    }
}
