package com.fantalol.backend.lineup;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class EffectiveLineupService {

    private static final int ROLE_COUNT = PlayerRole.values().length;

    private final EffectiveLineupPeriodRepository periodRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final UserService userService;
    private final LineupWindow lineupWindow;
    private final Clock clock;

    @Transactional(readOnly = true)
    public Set<LecPlayer> activePlayersAt(Long fantaTeamId, Instant playedAt) {
        return periodRepository.findActiveByFantaTeamId(fantaTeamId, playedAt).stream()
                .map(EffectiveLineupPeriod::getLecPlayer)
                .collect(java.util.stream.Collectors.toSet());
    }

    @Transactional(readOnly = true)
    public Optional<EffectiveLineupPeriod> activePeriodAt(Long fantaTeamId, PlayerRole role, Instant playedAt) {
        return periodRepository.findActiveByFantaTeamIdAndRole(fantaTeamId, role, playedAt);
    }

    @Transactional
    public void schedule(String username, Long fantaTeamId, Set<LecPlayer> players) {
        FantaTeam fantaTeam = fantaTeamRepository.findById(fantaTeamId)
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata con id: " + fantaTeamId));
        ensureOwnerOrAdmin(username, fantaTeam);
        if (isFixedRoster(fantaTeam)) {
            throw new BusinessRuleException("Nelle leghe con almeno 6 squadre la formazione coincide automaticamente con la rosa");
        }

        LineupWindow.Status status = lineupWindow.status(clock.instant());
        if (!status.editable()) {
            throw new BusinessRuleException("Le formazioni si possono modificare da martedì a giovedì");
        }
        validateFiveRoles(players);
        replaceOpenPeriods(fantaTeam, players, status.nextEffectiveAt(), LineupPeriodOrigin.USER);
    }

    @Transactional
    void createBackfillPeriods(FantaTeam fantaTeam, Set<LecPlayer> players, Instant effectiveFrom) {
        if (periodRepository.existsByFantaTeamId(fantaTeam.getId())) {
            return;
        }
        validateFiveRoles(players);
        List<EffectiveLineupPeriod> periods = newPeriods(fantaTeam, players, effectiveFrom, LineupPeriodOrigin.BACKFILL);
        periodRepository.saveAll(periods);
    }

    private void replaceOpenPeriods(FantaTeam fantaTeam, Set<LecPlayer> players, Instant effectiveFrom,
                                    LineupPeriodOrigin origin) {
        List<EffectiveLineupPeriod> openPeriods = periodRepository
                .findByFantaTeamIdAndEffectiveUntilIsNull(fantaTeam.getId());
        List<EffectiveLineupPeriod> pendingPeriods = openPeriods.stream()
                .filter(period -> !period.getEffectiveFrom().isBefore(effectiveFrom))
                .toList();
        if (!pendingPeriods.isEmpty()) {
            periodRepository.deleteAll(pendingPeriods);
            periodRepository.flush();
        }
        List<EffectiveLineupPeriod> changed = new ArrayList<>(openPeriods.stream()
                .filter(period -> period.getEffectiveFrom().isBefore(effectiveFrom))
                .toList());
        changed.forEach(period -> period.closeAt(effectiveFrom));
        changed.addAll(newPeriods(fantaTeam, players, effectiveFrom, origin));
        periodRepository.saveAll(changed);
    }

    private List<EffectiveLineupPeriod> newPeriods(FantaTeam fantaTeam, Set<LecPlayer> players,
                                                     Instant effectiveFrom, LineupPeriodOrigin origin) {
        return players.stream()
                .map(player -> EffectiveLineupPeriod.builder()
                        .fantaTeam(fantaTeam)
                        .role(player.getRuolo())
                        .lecPlayer(player)
                        .effectiveFrom(effectiveFrom)
                        .origin(origin)
                        .createdAt(clock.instant())
                        .build())
                .toList();
    }

    private void ensureOwnerOrAdmin(String username, FantaTeam fantaTeam) {
        if (!fantaTeam.getOwner().getUsername().equals(username)
                && userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN) {
            throw new BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica");
        }
    }

    private boolean isFixedRoster(FantaTeam fantaTeam) {
        Integer participants = fantaTeam.getLeague().getParticipantCount();
        return participants != null && participants >= 6;
    }

    private void validateFiveRoles(Set<LecPlayer> players) {
        if (players == null || players.size() != ROLE_COUNT
                || players.stream().map(LecPlayer::getId).distinct().count() != ROLE_COUNT
                || !EnumSet.allOf(PlayerRole.class).equals(players.stream()
                .map(LecPlayer::getRuolo).collect(java.util.stream.Collectors.toCollection(() -> EnumSet.noneOf(PlayerRole.class))))) {
            throw new BusinessRuleException("La formazione deve contenere esattamente un player per ruolo");
        }
    }
}
