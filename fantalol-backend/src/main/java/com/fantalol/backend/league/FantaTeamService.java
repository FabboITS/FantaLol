package com.fantalol.backend.league;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.dto.*;
import com.fantalol.backend.scoring.CumulativeScoringService;
import com.fantalol.backend.scoring.dto.CumulativeFantasyTeamScore;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Comparator;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.ArrayList;
import java.util.Collections;

/**
 * Gestisce le squadre fantacalcistiche (FantaTeam): iscrizione a una lega,
 * consultazione della rosa e logica dell'asta a crediti prefissati (senza
 * transazioni economiche reali).
 */
@Service
@RequiredArgsConstructor
public class FantaTeamService {

    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final LeagueService leagueService;
    private final UserService userService;
    private final LecPlayerRepository lecPlayerRepository;
    private final RosterPolicy rosterPolicy;
    private final CumulativeScoringService cumulativeScoringService;

    @Transactional
    public FantaTeamResponse joinLeague(String username, JoinLeagueRequest request) {
        User user = userService.findByUsernameOrThrow(username);
        League league = leagueService.getByInviteCodeOrThrow(request.codiceInvito());

        if (league.isCompetitionStarted()) {
            throw new BusinessRuleException("La lega è già iniziata: non è più possibile iscriversi");
        }

        if (fantaTeamRepository.countByLeagueId(league.getId()) >= 10) {
            throw new BusinessRuleException("La lega ha già raggiunto il limite di 10 squadre");
        }

        if (fantaTeamRepository.existsByLeagueIdAndOwnerId(league.getId(), user.getId())) {
            throw new BusinessRuleException("Sei già iscritto a questa lega con una squadra");
        }

        FantaTeam fantaTeam = FantaTeam.builder()
                .nome(request.nomeSquadra())
                .creditiResidui(league.getCreditiIniziali())
                .league(league)
                .owner(user)
                .build();

        return response(fantaTeamRepository.save(fantaTeam));
    }

    @Transactional(readOnly = true)
    public List<FantaTeamResponse> findByLeague(String username, Long leagueId) {
        leagueService.findById(username, leagueId);
        return fantaTeamRepository.findByLeagueId(leagueId).stream().map(this::response).toList();
    }

    @Transactional(readOnly = true)
    public List<FantaTeamResponse> findMine(String username) {
        return fantaTeamRepository.findByOwnerUsername(username).stream().map(this::response).toList();
    }

    @Transactional(readOnly = true)
    public FantaTeamResponse findById(String username, Long id) {
        FantaTeam team = getOrThrow(id);
        leagueService.findById(username, team.getLeague().getId());
        return response(team);
    }

    @Transactional(readOnly = true)
    public CumulativeFantasyTeamScore cumulativeScore(String username, Long id) {
        FantaTeam team = getOrThrow(id);
        leagueService.findById(username, team.getLeague().getId());
        return cumulativeScoringService.teamScore(id);
    }

    /**
     * Esegue l'acquisto (asta) di un player LEC per la FantaTeam indicata.
     * Regole di business applicate:
     * <ul>
     *     <li>solo il proprietario della squadra può acquistare per essa</li>
     *     <li>i crediti offerti non possono superare i crediti residui</li>
     *     <li>i crediti offerti non possono essere inferiori alla quotazione base del player</li>
     *     <li>il player non deve essere già stato acquistato da un'altra squadra della stessa lega</li>
     *     <li>la rosa rispetta i limiti dinamici determinati dal numero di squadre nella lega</li>
     * </ul>
     */
    @Transactional
    public RosterEntryResponse acquistaPlayer(String username, Long fantaTeamId, AcquistoPlayerRequest request) {
        FantaTeam fantaTeam = getOrThrow(fantaTeamId);
        assertOwner(fantaTeam, username);

        LecPlayer player = lecPlayerRepository.findByIdForUpdate(request.lecPlayerId())
                .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + request.lecPlayerId()));

        if (rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(fantaTeam.getLeague().getId(), player.getId())) {
            throw new BusinessRuleException("Il player " + player.getNickname() + " è già stato acquistato in questa lega");
        }

        if (request.creditiOfferti() > fantaTeam.getCreditiResidui()) {
            throw new BusinessRuleException("Crediti insufficienti: residui " + fantaTeam.getCreditiResidui()
                    + ", offerti " + request.creditiOfferti());
        }

        if (request.creditiOfferti() < player.getQuotazione()) {
            throw new BusinessRuleException("L'offerta (" + request.creditiOfferti()
                    + ") è inferiore alla quotazione base del player (" + player.getQuotazione() + ")");
        }

        List<RosterEntry> rosaAttuale = rosterEntryRepository.findByFantaTeamId(fantaTeam.getId());
        RosterPolicy.Limits limits = rosterPolicy.forLeague(fantaTeam.getLeague());
        if (rosaAttuale.size() >= limits.maxRosterSize()) {
            throw new BusinessRuleException("Rosa al completo: massimo " + limits.maxRosterSize() + " player");
        }

        long giocatoriStessoRuolo = rosaAttuale.stream()
                .filter(entry -> entry.getLecPlayer().getRuolo() == player.getRuolo())
                .count();
        if (giocatoriStessoRuolo >= limits.maxPerRole()) {
            throw new BusinessRuleException("Hai già raggiunto il numero massimo di player per il ruolo " + player.getRuolo());
        }

        RosterEntry entry = RosterEntry.builder()
                .fantaTeam(fantaTeam)
                .lecPlayer(player)
                .creditiSpesi(request.creditiOfferti())
                .build();

        fantaTeam.setCreditiResidui(fantaTeam.getCreditiResidui() - request.creditiOfferti());
        fantaTeamRepository.save(fantaTeam);

        return RosterEntryResponse.from(rosterEntryRepository.save(entry));
    }

    /**
     * Assegna gratuitamente il player disponibile meno costoso quando la squadra non può
     * permetterselo e tutte le altre squadre della lega hanno già completato la rosa.
     */
    @Transactional
    public RosterEntryResponse acquistaPlayerGratis(String username, Long fantaTeamId) {
        FantaTeam fantaTeam = getOrThrow(fantaTeamId);
        assertOwner(fantaTeam, username);
        List<RosterEntry> rosa = rosterEntryRepository.findByFantaTeamId(fantaTeamId);
        RosterPolicy.Limits limits = rosterPolicy.forLeague(fantaTeam.getLeague());
        if (rosa.size() >= limits.maxRosterSize()) {
            throw new BusinessRuleException("La rosa è già completa");
        }

        boolean altreRoseComplete = fantaTeamRepository.findByLeagueId(fantaTeam.getLeague().getId()).stream()
                .filter(team -> !team.getId().equals(fantaTeamId))
                .allMatch(team -> rosterEntryRepository.findByFantaTeamId(team.getId()).size() >= limits.maxRosterSize());
        if (!altreRoseComplete) {
            throw new BusinessRuleException("Il player gratis è disponibile solo quando tutte le altre squadre hanno completato la rosa");
        }

        Map<com.fantalol.backend.team.PlayerRole, Long> perRuolo = rosa.stream().collect(Collectors.groupingBy(
                entry -> entry.getLecPlayer().getRuolo(), Collectors.counting()));
        LecPlayer cheapest = lecPlayerRepository.findAll().stream()
                .filter(player -> perRuolo.getOrDefault(player.getRuolo(), 0L) < limits.maxPerRole())
                .filter(player -> !rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(
                        fantaTeam.getLeague().getId(), player.getId()))
                .min(Comparator.comparingInt(LecPlayer::getQuotazione))
                .orElseThrow(() -> new BusinessRuleException("Non ci sono player disponibili per completare la rosa"));

        if (fantaTeam.getCreditiResidui() >= cheapest.getQuotazione()) {
            throw new BusinessRuleException("Hai ancora abbastanza crediti per acquistare il player disponibile meno costoso");
        }

        LecPlayer lockedPlayer = lecPlayerRepository.findByIdForUpdate(cheapest.getId())
                .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + cheapest.getId()));
        if (rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(fantaTeam.getLeague().getId(), lockedPlayer.getId())) {
            throw new BusinessRuleException("Il player è appena stato acquistato da un'altra squadra: riprova");
        }

        return RosterEntryResponse.from(rosterEntryRepository.save(RosterEntry.builder()
                .fantaTeam(fantaTeam)
                .lecPlayer(lockedPlayer)
                .creditiSpesi(0)
                .build()));
    }

    /** Completa gratuitamente e casualmente i ruoli mancanti quando nessun player idoneo è acquistabile. */
    @Transactional
    public FantaTeamResponse completaRosaCasualmente(String username, Long fantaTeamId) {
        FantaTeam team = getOrThrow(fantaTeamId);
        assertOwner(team, username);
        List<RosterEntry> roster = rosterEntryRepository.findByFantaTeamId(fantaTeamId);
        RosterPolicy.Limits limits = rosterPolicy.forLeague(team.getLeague());
        if (roster.size() >= limits.maxRosterSize()) throw new BusinessRuleException("La rosa è già completa");

        Map<com.fantalol.backend.team.PlayerRole, Long> counts = roster.stream().collect(Collectors.groupingBy(
                e -> e.getLecPlayer().getRuolo(), Collectors.counting()));
        List<LecPlayer> available = lecPlayerRepository.findAll().stream()
                .filter(p -> counts.getOrDefault(p.getRuolo(), 0L) < limits.maxPerRole())
                .filter(p -> !rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(team.getLeague().getId(), p.getId()))
                .toList();
        int cheapest = available.stream().mapToInt(LecPlayer::getQuotazione).min()
                .orElseThrow(() -> new BusinessRuleException("Non ci sono abbastanza player disponibili"));
        if (team.getCreditiResidui() >= cheapest)
            throw new BusinessRuleException("Puoi ancora permetterti un player disponibile: continua con l'asta");

        List<LecPlayer> selected = new ArrayList<>();
        for (var role : com.fantalol.backend.team.PlayerRole.values()) {
            int missing = limits.maxPerRole() - counts.getOrDefault(role, 0L).intValue();
            List<LecPlayer> rolePlayers = new ArrayList<>(available.stream().filter(p -> p.getRuolo() == role).toList());
            Collections.shuffle(rolePlayers);
            if (rolePlayers.size() < missing)
                throw new BusinessRuleException("Non ci sono abbastanza player disponibili nel ruolo " + role);
            selected.addAll(rolePlayers.subList(0, missing));
        }
        for (LecPlayer candidate : selected) {
            LecPlayer locked = lecPlayerRepository.findByIdForUpdate(candidate.getId())
                    .orElseThrow(() -> new ResourceNotFoundException("Player non trovato"));
            if (rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(team.getLeague().getId(), locked.getId()))
                throw new BusinessRuleException("Un player casuale è appena stato assegnato: riprova");
            rosterEntryRepository.save(RosterEntry.builder().fantaTeam(team).lecPlayer(locked).creditiSpesi(0).build());
        }
        return response(team);
    }

    @Transactional
    public void rilasciaPlayer(String username, Long fantaTeamId, Long rosterEntryId) {
        FantaTeam fantaTeam = getOrThrow(fantaTeamId);
        assertOwner(fantaTeam, username);

        RosterEntry entry = rosterEntryRepository.findById(rosterEntryId)
                .orElseThrow(() -> new ResourceNotFoundException("Voce di rosa non trovata con id: " + rosterEntryId));

        if (!entry.getFantaTeam().getId().equals(fantaTeam.getId())) {
            throw new BusinessRuleException("La voce di rosa indicata non appartiene a questa squadra");
        }

        // Rimborso parziale (50%) dei crediti spesi, per disincentivare acquisti/rilasci speculativi.
        int rimborso = entry.getCreditiSpesi() / 2;
        fantaTeam.setCreditiResidui(fantaTeam.getCreditiResidui() + rimborso);
        fantaTeamRepository.save(fantaTeam);

        rosterEntryRepository.delete(entry);
    }

    private void assertOwner(FantaTeam fantaTeam, String username) {
        if (!fantaTeam.getOwner().getUsername().equals(username)
                && userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN) {
            throw new BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica");
        }
    }

    FantaTeam getOrThrow(Long id) {
        return fantaTeamRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata con id: " + id));
    }

    private FantaTeamResponse response(FantaTeam team) {
        return FantaTeamResponse.from(team);
    }
}
