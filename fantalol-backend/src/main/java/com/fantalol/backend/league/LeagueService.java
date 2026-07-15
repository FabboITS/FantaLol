package com.fantalol.backend.league;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.dto.LeagueRequest;
import com.fantalol.backend.league.dto.LeagueResponse;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import com.fantalol.backend.user.Role;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Gestisce la creazione e la consultazione delle leghe private.
 */
@Service
@RequiredArgsConstructor
public class LeagueService {

    private final LeagueRepository leagueRepository;
    private final UserService userService;

    @Transactional(readOnly = true)
    public List<LeagueResponse> findAll() {
        return leagueRepository.findAll().stream().map(LeagueResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public LeagueResponse findById(Long id) {
        return LeagueResponse.from(getOrThrow(id));
    }

    @Transactional
    public LeagueResponse create(String adminUsername, LeagueRequest request) {
        User admin = userService.findByUsernameOrThrow(adminUsername);

        League league = League.builder()
                .nome(request.nome())
                .creditiIniziali(request.creditiIniziali() != null ? request.creditiIniziali() : 1000)
                .admin(admin)
                .build();

        return LeagueResponse.from(leagueRepository.save(league));
    }

    @Transactional
    public void delete(String username, Long leagueId) {
        League league = getOrThrow(leagueId);
        User user = userService.findByUsernameOrThrow(username);
        if (user.getRole() != Role.ADMIN && !league.getAdmin().getUsername().equals(username)) {
            throw new BusinessRuleException("Solo l'admin della lega può cancellarla");
        }
        leagueRepository.delete(league);
    }

    public League getOrThrow(Long id) {
        return leagueRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Lega non trovata con id: " + id));
    }

    League getByInviteCodeOrThrow(String codiceInvito) {
        return leagueRepository.findByCodiceInvito(codiceInvito)
                .orElseThrow(() -> new BusinessRuleException("Nessuna lega trovata con codice invito: " + codiceInvito));
    }
}
