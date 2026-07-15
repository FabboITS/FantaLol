package com.fantalol.backend.matchday;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.league.FantaTeam;
import com.fantalol.backend.league.FantaTeamRepository;
import com.fantalol.backend.league.League;
import com.fantalol.backend.league.RosterEntryRepository;
import com.fantalol.backend.matchday.dto.FormationRequest;
import com.fantalol.backend.matchday.dto.FormationResponse;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import com.fantalol.backend.team.PlayerRole;
import com.fantalol.backend.user.User;
import com.fantalol.backend.user.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class FormationServiceTest {

    @Mock
    private FormationRepository formationRepository;
    @Mock
    private FantaTeamRepository fantaTeamRepository;
    @Mock
    private RosterEntryRepository rosterEntryRepository;
    @Mock
    private LecPlayerRepository lecPlayerRepository;
    @Mock
    private MatchdayRepository matchdayRepository;
    @Mock
    private UserService userService;

    @InjectMocks
    private FormationService formationService;

    private User owner;
    private FantaTeam fantaTeam;
    private Matchday matchday;
    private LecPlayer caps;

    @BeforeEach
    void setUp() {
        owner = User.builder().id(1L).username("mago").build();
        League league = League.builder().id(1L).build();
        fantaTeam = FantaTeam.builder().id(1L).nome("Team").owner(owner).league(league).build();
        matchday = Matchday.builder().id(1L).numero(1).chiusa(false).build();
        caps = LecPlayer.builder().id(10L).nickname("Caps").ruolo(PlayerRole.MID).build();
    }

    @Test
    void impostaCorrettamenteUnaFormazioneValida() {
        List<LecPlayer> titolari = List.of(
                LecPlayer.builder().id(11L).nickname("Top").ruolo(PlayerRole.TOP).build(),
                LecPlayer.builder().id(12L).nickname("Jungle").ruolo(PlayerRole.JUNGLE).build(),
                caps,
                LecPlayer.builder().id(13L).nickname("Adc").ruolo(PlayerRole.ADC).build(),
                LecPlayer.builder().id(14L).nickname("Support").ruolo(PlayerRole.SUPPORT).build()
        );
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(matchdayRepository.findById(1L)).thenReturn(Optional.of(matchday));
        for (LecPlayer player : titolari) {
            when(rosterEntryRepository.existsByFantaTeamIdAndLecPlayerId(1L, player.getId())).thenReturn(true);
            when(lecPlayerRepository.findById(player.getId())).thenReturn(Optional.of(player));
        }
        when(formationRepository.findByFantaTeamIdAndMatchdayId(1L, 1L)).thenReturn(Optional.empty());
        when(formationRepository.save(any(Formation.class))).thenAnswer(inv -> inv.getArgument(0));

        FormationRequest request = new FormationRequest(1L, titolari.stream().map(LecPlayer::getId).toList(), 10L);
        FormationResponse response = formationService.impostaFormazione("mago", 1L, request);

        assertThat(response.titolari()).containsExactlyInAnyOrder("Top", "Jungle", "Caps", "Adc", "Support");
        assertThat(response.capitano()).isEqualTo("Caps");
    }

    @Test
    void rifiutaSeIlPlayerNonEInRosa() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(matchdayRepository.findById(1L)).thenReturn(Optional.of(matchday));
        when(rosterEntryRepository.existsByFantaTeamIdAndLecPlayerId(1L, 10L)).thenReturn(false);

        FormationRequest request = new FormationRequest(1L, List.of(10L, 11L, 12L, 13L, 14L), null);

        assertThatThrownBy(() -> formationService.impostaFormazione("mago", 1L, request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("non appartiene alla rosa");
    }

    @Test
    void rifiutaSeIlCapitanoNonEUnoDeiTitolari() {
        List<LecPlayer> titolari = List.of(
                LecPlayer.builder().id(11L).nickname("Top").ruolo(PlayerRole.TOP).build(),
                LecPlayer.builder().id(12L).nickname("Jungle").ruolo(PlayerRole.JUNGLE).build(),
                caps,
                LecPlayer.builder().id(13L).nickname("Adc").ruolo(PlayerRole.ADC).build(),
                LecPlayer.builder().id(14L).nickname("Support").ruolo(PlayerRole.SUPPORT).build()
        );
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(matchdayRepository.findById(1L)).thenReturn(Optional.of(matchday));
        for (LecPlayer player : titolari) {
            when(rosterEntryRepository.existsByFantaTeamIdAndLecPlayerId(1L, player.getId())).thenReturn(true);
            when(lecPlayerRepository.findById(player.getId())).thenReturn(Optional.of(player));
        }

        FormationRequest request = new FormationRequest(1L, titolari.stream().map(LecPlayer::getId).toList(), 999L);

        assertThatThrownBy(() -> formationService.impostaFormazione("mago", 1L, request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("capitano");
    }

    @Test
    void rifiutaSeNonSiEIlProprietarioDellaSquadra() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(userService.findByUsernameOrThrow("altro-utente"))
                .thenReturn(User.builder().username("altro-utente").role(com.fantalol.backend.user.Role.USER).build());

        FormationRequest request = new FormationRequest(1L, List.of(10L), null);

        assertThatThrownBy(() -> formationService.impostaFormazione("altro-utente", 1L, request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("proprietario");
    }

    @Test
    void rifiutaSeLaGiornataEGiaChiusa() {
        Matchday chiusa = Matchday.builder().id(2L).numero(2).chiusa(true).build();
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(matchdayRepository.findById(2L)).thenReturn(Optional.of(chiusa));

        FormationRequest request = new FormationRequest(2L, List.of(10L), null);

        assertThatThrownBy(() -> formationService.impostaFormazione("mago", 1L, request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("chiusa");
    }
}
