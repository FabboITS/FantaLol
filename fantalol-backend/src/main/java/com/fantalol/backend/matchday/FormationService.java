package com.fantalol.backend.matchday;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.matchday.dto.FormationRequest;
import com.fantalol.backend.matchday.dto.FormationResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.user.Role;
import com.fantalol.backend.user.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Gestisce la formazione (titolari + capitano) che ogni FantaTeam schiera per una giornata.
 */
@Service
@RequiredArgsConstructor
public class FormationService {

    private static final int NUMERO_TITOLARI = 5;

    private final FormationRepository formationRepository;
    private final FantaTeamRepository fantaTeamRepository;
    private final RosterEntryRepository rosterEntryRepository;
    private final LecPlayerRepository lecPlayerRepository;
    private final MatchdayRepository matchdayRepository;
    private final UserService userService;

    @Transactional(readOnly = true)
    public FormationResponse findByTeamAndMatchday(Long fantaTeamId, Long matchdayId) {
        Formation formation = formationRepository.findByFantaTeamIdAndMatchdayId(fantaTeamId, matchdayId)
                .orElseThrow(() -> new ResourceNotFoundException("Nessuna formazione trovata per la squadra e la giornata indicate"));
        return FormationResponse.from(formation);
    }

    /**
     * Imposta (o sovrascrive) la formazione di una FantaTeam per una giornata.
     * Regole di business:
     * <ul>
     *     <li>solo il proprietario della squadra può schierare la formazione</li>
     *     <li>devono essere schierati esattamente {@value #NUMERO_TITOLARI} titolari, uno per ruolo</li>
     *     <li>tutti i titolari devono appartenere alla rosa acquistata all'asta dalla squadra</li>
     *     <li>il capitano (opzionale) deve essere uno dei titolari schierati</li>
     * </ul>
     */
    @Transactional
    public FormationResponse impostaFormazione(String username, Long fantaTeamId, FormationRequest request) {
        FantaTeam fantaTeam = fantaTeamRepository.findById(fantaTeamId)
                .orElseThrow(() -> new ResourceNotFoundException("FantaTeam non trovata con id: " + fantaTeamId));

        if (!fantaTeam.getOwner().getUsername().equals(username)
                && userService.findByUsernameOrThrow(username).getRole() != Role.ADMIN) {
            throw new BusinessRuleException("Non sei il proprietario di questa squadra fantacalcistica");
        }

        var matchday = matchdayRepository.findById(request.matchdayId())
                .orElseThrow(() -> new ResourceNotFoundException("Giornata non trovata con id: " + request.matchdayId()));

        if (matchday.isChiusa()) {
            throw new BusinessRuleException("La giornata " + matchday.getNumero() + " è chiusa: non puoi modificare la formazione");
        }

        List<Long> titolariIds = request.titolariIds();
        if (titolariIds.size() != NUMERO_TITOLARI || new HashSet<>(titolariIds).size() != NUMERO_TITOLARI) {
            throw new BusinessRuleException("Devi schierare esattamente " + NUMERO_TITOLARI + " titolari diversi");
        }

        Set<LecPlayer> titolari = new HashSet<>();
        for (Long playerId : titolariIds) {
            if (!rosterEntryRepository.existsByFantaTeamIdAndLecPlayerId(fantaTeamId, playerId)) {
                throw new BusinessRuleException("Il player con id " + playerId + " non appartiene alla rosa di questa squadra");
            }
            LecPlayer player = lecPlayerRepository.findById(playerId)
                    .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + playerId));
            titolari.add(player);
        }

        if (titolari.stream().map(LecPlayer::getRuolo).distinct().count() != NUMERO_TITOLARI) {
            throw new BusinessRuleException("La formazione deve contenere un player per ruolo: TOP, JUNGLE, MID, ADC e SUPPORT");
        }

        LecPlayer capitano = null;
        if (request.capitanoId() != null) {
            if (!titolariIds.contains(request.capitanoId())) {
                throw new BusinessRuleException("Il capitano deve essere uno dei titolari schierati");
            }
            capitano = titolari.stream()
                    .filter(p -> p.getId().equals(request.capitanoId()))
                    .findFirst()
                    .orElseThrow(() -> new ResourceNotFoundException("Player LEC non trovato con id: " + request.capitanoId()));
        }

        Formation formation = formationRepository.findByFantaTeamIdAndMatchdayId(fantaTeamId, request.matchdayId())
                .orElse(Formation.builder().fantaTeam(fantaTeam).matchday(matchday).build());

        formation.setTitolari(titolari);
        formation.setCapitano(capitano);

        return FormationResponse.from(formationRepository.save(formation));
    }
}
