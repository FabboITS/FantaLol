package com.fantalol.backend.league;

import com.fantalol.backend.common.*;
import com.fantalol.backend.league.dto.*;
import com.fantalol.backend.team.*;
import com.fantalol.backend.user.*;
import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AuctionService {
    private static final int SECONDS_PER_BID = 15;

    private final AuctionSessionRepository auctionRepository;
    private final LeagueRepository leagueRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterRepository;
    private final LecPlayerRepository playerRepository;
    private final UserService userService;
    private final RosterPolicy rosterPolicy;

    @Transactional
    public AuctionResponse start(String username, AuctionStartRequest request) {
        League league = leagueRepository.findByIdForUpdate(request.leagueId())
                .orElseThrow(() -> new ResourceNotFoundException("Lega non trovata con id: " + request.leagueId()));
        assertAuctionOpen(league);
        assertParticipantOrAdmin(username, league);
        auctionRepository.findFirstByLeagueIdAndStatus(league.getId(), AuctionStatus.ACTIVE)
                .ifPresent(a -> { throw new BusinessRuleException("C'è già un'asta attiva in questa lega"); });
        LecPlayer player = playerRepository.findByIdForUpdate(request.lecPlayerId())
                .orElseThrow(() -> new ResourceNotFoundException("Player non trovato"));
        if (rosterRepository.existsByFantaTeam_League_IdAndLecPlayerId(league.getId(), player.getId())) {
            throw new BusinessRuleException("Questo player è già assegnato nella lega");
        }
        FantaTeam openingBidder = fantaTeamRepository.findById(request.fantaTeamId())
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata"));
        if (!openingBidder.getLeague().getId().equals(league.getId())) {
            throw new BusinessRuleException("La squadra non partecipa a questa lega");
        }
        assertOwnerOrAdmin(username, openingBidder);
        validateRosterSlot(openingBidder, player);
        if (openingBidder.getCreditiResidui() < player.getQuotazione()) {
            throw new BusinessRuleException("Crediti insufficienti per avviare l'asta");
        }
        return AuctionResponse.from(auctionRepository.save(AuctionSession.builder()
                .league(league).player(player).currentBid(player.getQuotazione())
                .highestBidder(openingBidder)
                .endsAt(Instant.now().plus(SECONDS_PER_BID, ChronoUnit.SECONDS))
                .status(AuctionStatus.ACTIVE).build()));
    }

    @Transactional
    public AuctionResponse bid(String username, Long auctionId, AuctionBidRequest request) {
        AuctionSession auction = auctionRepository.findByIdForUpdate(auctionId)
                .orElseThrow(() -> new ResourceNotFoundException("Asta non trovata"));
        assertAuctionOpen(auction.getLeague());
        if (auction.getStatus() != AuctionStatus.ACTIVE || !auction.getEndsAt().isAfter(Instant.now())) {
            finalizeAuction(auction);
            throw new BusinessRuleException("L'asta è terminata");
        }
        FantaTeam team = fantaTeamRepository.findById(request.fantaTeamId())
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata"));
        if (!team.getLeague().getId().equals(auction.getLeague().getId())) {
            throw new BusinessRuleException("La squadra non partecipa a questa lega");
        }
        assertOwnerOrAdmin(username, team);
        if (auction.getHighestBidder() != null
                && auction.getHighestBidder().getId().equals(team.getId())) {
            throw new BusinessRuleException("Sei già il miglior offerente");
        }
        int minimum = auction.getHighestBidder() == null ? auction.getCurrentBid() : auction.getCurrentBid() + 1;
        if (request.credits() < minimum) throw new BusinessRuleException("L'offerta minima è " + minimum + " crediti");
        if (request.credits() > team.getCreditiResidui()) throw new BusinessRuleException("Crediti insufficienti");
        validateRosterSlot(team, auction.getPlayer());
        auction.setHighestBidder(team);
        auction.setCurrentBid(request.credits());
        auction.setEndsAt(Instant.now().plus(SECONDS_PER_BID, ChronoUnit.SECONDS));
        return AuctionResponse.from(auctionRepository.save(auction));
    }

    @Transactional(readOnly = true)
    public AuctionResponse active(Long leagueId) {
        return auctionRepository.findFirstByLeagueIdAndStatus(leagueId, AuctionStatus.ACTIVE)
                .map(AuctionResponse::from).orElse(null);
    }

    @Scheduled(fixedDelay = 500)
    @Transactional
    public void finalizeExpired() {
        auctionRepository.findByStatusAndEndsAtLessThanEqual(AuctionStatus.ACTIVE, Instant.now())
                .forEach(a -> auctionRepository.findByIdForUpdate(a.getId()).ifPresent(this::finalizeAuction));
    }

    private void finalizeAuction(AuctionSession auction) {
        if (auction.getStatus() != AuctionStatus.ACTIVE) return;
        FantaTeam winner = auction.getHighestBidder();
        if (winner == null) {
            auction.setStatus(AuctionStatus.EXPIRED);
        } else if (winner.getCreditiResidui() >= auction.getCurrentBid()
                && !rosterRepository.existsByFantaTeam_League_IdAndLecPlayerId(auction.getLeague().getId(), auction.getPlayer().getId())) {
            validateRosterSlot(winner, auction.getPlayer());
            winner.setCreditiResidui(winner.getCreditiResidui() - auction.getCurrentBid());
            fantaTeamRepository.save(winner);
            rosterRepository.save(RosterEntry.builder().fantaTeam(winner).lecPlayer(auction.getPlayer())
                    .creditiSpesi(auction.getCurrentBid()).build());
            auction.setStatus(AuctionStatus.WON);
        } else {
            auction.setStatus(AuctionStatus.EXPIRED);
        }
        auctionRepository.save(auction);
    }

    private void validateRosterSlot(FantaTeam team, LecPlayer player) {
        List<RosterEntry> roster = rosterRepository.findByFantaTeamId(team.getId());
        RosterPolicy.Limits limits = rosterPolicy.forLeague(team.getLeague());
        if (roster.size() >= limits.maxRosterSize()) throw new BusinessRuleException("Rosa già completa");
        if (roster.stream().filter(e -> e.getLecPlayer().getRuolo() == player.getRuolo()).count() >= limits.maxPerRole())
            throw new BusinessRuleException("Hai già raggiunto il limite per il ruolo " + player.getRuolo());
    }

    private void assertParticipantOrAdmin(String username, League league) {
        User user = userService.findByUsernameOrThrow(username);
        if (user.getRole() != Role.ADMIN && fantaTeamRepository.findByLeagueIdAndOwnerUsername(league.getId(), username).isEmpty())
            throw new BusinessRuleException("Non partecipi a questa lega");
    }

    private void assertOwnerOrAdmin(String username, FantaTeam team) {
        if (!team.getOwner().getUsername().equals(username)
                && userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN)
            throw new BusinessRuleException("Non puoi offrire per questa squadra");
    }

    private void assertAuctionOpen(League league) {
        if (!league.isAuctionOpen()) {
            throw new BusinessRuleException("L'asta della lega non è aperta");
        }
    }
}
