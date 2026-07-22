package com.fantalol.backend.league;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.dto.LeagueRequest;
import com.fantalol.backend.league.dto.LeagueResponse;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.PlayerRole;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Sort;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Gestisce la creazione e la consultazione delle leghe private.
 */
@Service
@RequiredArgsConstructor
public class LeagueService {

    private final LeagueRepository leagueRepository;
    private final UserService userService;
    private final AuctionSessionRepository auctionSessionRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final RosterPolicy rosterPolicy;

    @Transactional(readOnly = true)
    public List<LeagueResponse> findAll(String username) {
        User user = userService.findByUsernameOrThrow(username);
        List<League> leagues = user.getRole() == Role.ADMIN
                ? leagueRepository.findAll(Sort.by(Sort.Direction.ASC, "id"))
                : leagueRepository.findAccessibleByUsername(username);
        return leagues.stream().map(LeagueResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public LeagueResponse findById(String username, Long id) {
        User user = userService.findByUsernameOrThrow(username);
        League league = getOrThrow(id);
        boolean isCreator = league.getAdmin().getUsername().equals(username);
        boolean isMember = fantaTeamRepository.findByLeagueIdAndOwnerUsername(id, username).isPresent();
        if (user.getRole() != Role.ADMIN && !isCreator && !isMember) {
            throw new AccessDeniedException("You cannot access this league");
        }
        return LeagueResponse.from(league);
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
            throw new AccessDeniedException("You cannot delete this league");
        }
        leagueRepository.delete(league);
    }

    @Transactional
    public LeagueResponse openAuction(String username, Long leagueId) {
        League league = getForUpdateOrThrow(leagueId);
        assertLeagueCreatorOrGlobalAdmin(username, league);
        if (!league.isCompetitionStarted()) {
            throw new BusinessRuleException("Crea una giornata prima di aprire l'asta");
        }
        league.setAuctionOpen(true);
        return LeagueResponse.from(leagueRepository.save(league));
    }

    @Transactional
    public LeagueResponse closeAuction(String username, Long leagueId) {
        League league = getForUpdateOrThrow(leagueId);
        assertLeagueCreatorOrGlobalAdmin(username, league);
        if (auctionSessionRepository.findFirstByLeagueIdAndStatus(leagueId, AuctionStatus.ACTIVE).isPresent()) {
            throw new BusinessRuleException("Attendi la fine dell'asta del player prima di terminare l'asta della lega");
        }
        league.setAuctionOpen(false);
        return LeagueResponse.from(leagueRepository.save(league));
    }

    @Transactional
    public League startCompetitionAndOpenAuction(League league) {
        league.freezeParticipantCount(Math.toIntExact(fantaTeamRepository.countByLeagueId(league.getId())));
        league.setAuctionOpen(true);
        return leagueRepository.save(league);
    }

    @Transactional
    public List<com.fantalol.backend.league.dto.FantaTeamResponse> completeAllRostersRandomly(
            String username, Long leagueId) {
        League league = getForUpdateOrThrow(leagueId);
        assertLeagueCreatorOrGlobalAdmin(username, league);
        if (league.isAuctionOpen()) {
            throw new BusinessRuleException("Termina l'asta della lega prima di completare casualmente le rose");
        }

        RosterPolicy.Limits limits = rosterPolicy.forLeague(league);
        List<FantaTeam> teams = fantaTeamRepository.findByLeagueId(leagueId);
        List<LecPlayer> available = new ArrayList<>(lecPlayerRepository.findAll().stream()
                .filter(player -> !rosterEntryRepository
                        .existsByFantaTeam_League_IdAndLecPlayerId(leagueId, player.getId()))
                .toList());
        Collections.shuffle(available);

        Map<PlayerRole, List<LecPlayer>> byRole = available.stream()
                .collect(Collectors.groupingBy(LecPlayer::getRuolo,
                        () -> new EnumMap<>(PlayerRole.class), Collectors.toCollection(ArrayList::new)));
        Map<FantaTeam, List<LecPlayer>> assignments = new java.util.LinkedHashMap<>();

        for (FantaTeam team : teams) {
            List<RosterEntry> current = rosterEntryRepository.findByFantaTeamId(team.getId());
            if (current.size() >= limits.maxRosterSize()) {
                continue;
            }
            Map<PlayerRole, Long> counts = current.stream().collect(Collectors.groupingBy(
                    entry -> entry.getLecPlayer().getRuolo(), () -> new EnumMap<>(PlayerRole.class),
                    Collectors.counting()));
            List<LecPlayer> selected = new ArrayList<>();
            for (PlayerRole role : PlayerRole.values()) {
                int missing = limits.maxPerRole() - counts.getOrDefault(role, 0L).intValue();
                List<LecPlayer> rolePool = byRole.computeIfAbsent(role, ignored -> new ArrayList<>());
                if (rolePool.size() < missing) {
                    throw new BusinessRuleException("Non ci sono abbastanza player disponibili per completare tutte le rose");
                }
                for (int i = 0; i < missing; i++) {
                    selected.add(rolePool.remove(rolePool.size() - 1));
                }
            }
            assignments.put(team, selected);
        }

        Set<Long> assignedIds = new HashSet<>();
        assignments.forEach((team, players) -> players.forEach(player -> {
            if (!assignedIds.add(player.getId())) {
                throw new BusinessRuleException("Un player casuale è stato selezionato più volte");
            }
            RosterEntry entry = rosterEntryRepository.save(RosterEntry.builder()
                    .fantaTeam(team).lecPlayer(player).creditiSpesi(0).build());
            team.getRosa().add(entry);
        }));

        return teams.stream().map(com.fantalol.backend.league.dto.FantaTeamResponse::from).toList();
    }

    public League getOrThrow(Long id) {
        return leagueRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Lega non trovata con id: " + id));
    }

    League getByInviteCodeOrThrow(String codiceInvito) {
        return leagueRepository.findByCodiceInvito(codiceInvito)
                .orElseThrow(() -> new BusinessRuleException("Nessuna lega trovata con codice invito: " + codiceInvito));
    }

    private League getForUpdateOrThrow(Long id) {
        return leagueRepository.findByIdForUpdate(id)
                .orElseThrow(() -> new ResourceNotFoundException("Lega non trovata con id: " + id));
    }

    private void assertLeagueCreatorOrGlobalAdmin(String username, League league) {
        User user = userService.findByUsernameOrThrow(username);
        if (user.getRole() != Role.ADMIN && !league.getAdmin().getUsername().equals(username)) {
            throw new BusinessRuleException("Solo il creatore della lega può gestire l'asta");
        }
    }
}
