package com.fantalol.backend.league;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.league.dto.AcquistoPlayerRequest;
import com.fantalol.backend.league.dto.JoinLeagueRequest;
import com.fantalol.backend.league.dto.RosterEntryResponse;
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
class FantaTeamServiceTest {

    @Mock
    private FantaTeamRepository fantaTeamRepository;
    @Mock
    private RosterEntryRepository rosterEntryRepository;
    @Mock
    private LeagueService leagueService;
    @Mock
    private UserService userService;
    @Mock
    private LecPlayerRepository lecPlayerRepository;
    @Mock
    private RosterPolicy rosterPolicy;

    @InjectMocks
    private FantaTeamService fantaTeamService;

    private User user;
    private League league;
    private FantaTeam fantaTeam;
    private LecPlayer player;

    @BeforeEach
    void setUp() {
        user = User.builder().id(1L).username("mago").build();
        league = League.builder().id(1L).nome("Lega Test").codiceInvito("ABC12345").creditiIniziali(500).admin(user).build();
        fantaTeam = FantaTeam.builder().id(1L).nome("I Signori del Rift").creditiResidui(500).league(league).owner(user).build();
        player = LecPlayer.builder().id(10L).nickname("Caps").ruolo(PlayerRole.MID).quotazione(80).build();
        lenient().when(rosterPolicy.forLeague(league)).thenReturn(new RosterPolicy.Limits(10, 2));
    }

    @Test
    void nonPermetteUnaUndicesimaSquadra() {
        when(userService.findByUsernameOrThrow("mago")).thenReturn(user);
        when(leagueService.getByInviteCodeOrThrow("ABC12345")).thenReturn(league);
        when(fantaTeamRepository.countByLeagueId(1L)).thenReturn(10L);

        assertThatThrownBy(() -> fantaTeamService.joinLeague("mago",
                new JoinLeagueRequest("ABC12345", "Team 11")))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessage("La lega ha già raggiunto il limite di 10 squadre");
    }

    @Test
    void iscriveUnUtenteAdUnaLega() {
        when(userService.findByUsernameOrThrow("mago")).thenReturn(user);
        when(leagueService.getByInviteCodeOrThrow("ABC12345")).thenReturn(league);
        when(fantaTeamRepository.existsByLeagueIdAndOwnerId(1L, 1L)).thenReturn(false);
        when(fantaTeamRepository.save(any(FantaTeam.class))).thenAnswer(inv -> {
            FantaTeam ft = inv.getArgument(0);
            ft.setId(1L);
            return ft;
        });

        var response = fantaTeamService.joinLeague("mago", new JoinLeagueRequest("ABC12345", "I Signori del Rift"));

        assertThat(response.nome()).isEqualTo("I Signori del Rift");
        assertThat(response.creditiResidui()).isEqualTo(500);
    }

    @Test
    void nonPermetteDiIscriversiDueVolteAllaStessaLega() {
        when(userService.findByUsernameOrThrow("mago")).thenReturn(user);
        when(leagueService.getByInviteCodeOrThrow("ABC12345")).thenReturn(league);
        when(fantaTeamRepository.existsByLeagueIdAndOwnerId(1L, 1L)).thenReturn(true);

        assertThatThrownBy(() -> fantaTeamService.joinLeague("mago", new JoinLeagueRequest("ABC12345", "Team 2")))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("già iscritto");
    }

    @Test
    void acquistaCorrettamenteUnPlayerAllAsta() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(lecPlayerRepository.findByIdForUpdate(10L)).thenReturn(Optional.of(player));
        when(rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(1L, 10L)).thenReturn(false);
        when(rosterEntryRepository.findByFantaTeamId(1L)).thenReturn(List.of());
        when(rosterEntryRepository.save(any(RosterEntry.class))).thenAnswer(inv -> {
            RosterEntry entry = inv.getArgument(0);
            entry.setId(100L);
            return entry;
        });

        RosterEntryResponse response = fantaTeamService.acquistaPlayer("mago", 1L, new AcquistoPlayerRequest(10L, 90));

        assertThat(response.creditiSpesi()).isEqualTo(90);
        assertThat(fantaTeam.getCreditiResidui()).isEqualTo(410);
    }

    @Test
    void nonPermetteAcquistoSeCreditiInsufficienti() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(lecPlayerRepository.findByIdForUpdate(10L)).thenReturn(Optional.of(player));
        when(rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(1L, 10L)).thenReturn(false);

        assertThatThrownBy(() -> fantaTeamService.acquistaPlayer("mago", 1L, new AcquistoPlayerRequest(10L, 900)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("Crediti insufficienti");
    }

    @Test
    void nonPermetteAcquistoSeOffertaSottoQuotazione() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(lecPlayerRepository.findByIdForUpdate(10L)).thenReturn(Optional.of(player));
        when(rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(1L, 10L)).thenReturn(false);

        assertThatThrownBy(() -> fantaTeamService.acquistaPlayer("mago", 1L, new AcquistoPlayerRequest(10L, 10)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("inferiore alla quotazione");
    }

    @Test
    void nonPermetteAcquistoSeIlPlayerEGiaStatoPreso() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(lecPlayerRepository.findByIdForUpdate(10L)).thenReturn(Optional.of(player));
        when(rosterEntryRepository.existsByFantaTeam_League_IdAndLecPlayerId(1L, 10L)).thenReturn(true);

        assertThatThrownBy(() -> fantaTeamService.acquistaPlayer("mago", 1L, new AcquistoPlayerRequest(10L, 90)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("già stato acquistato");
    }

    @Test
    void nonPermetteAcquistoAChiNonEProprietarioDellaSquadra() {
        when(fantaTeamRepository.findById(1L)).thenReturn(Optional.of(fantaTeam));
        when(userService.findByUsernameOrThrow("altro-utente"))
                .thenReturn(User.builder().username("altro-utente").role(com.fantalol.backend.user.Role.USER).build());

        assertThatThrownBy(() -> fantaTeamService.acquistaPlayer("altro-utente", 1L, new AcquistoPlayerRequest(10L, 90)))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("proprietario");
    }
}
