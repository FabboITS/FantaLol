package com.fantalol.backend.team;

import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.team.dto.LecPlayerRequest;
import com.fantalol.backend.team.dto.LecPlayerResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class LecPlayerServiceTest {

    @Mock
    private LecPlayerRepository lecPlayerRepository;
    @Mock
    private LecTeamRepository lecTeamRepository;

    @InjectMocks
    private LecPlayerService lecPlayerService;

    @Test
    void creaUnNuovoPlayerAssociatoAlTeam() {
        LecTeam team = LecTeam.builder().id(1L).nome("G2 Esports").build();
        LecPlayerRequest request = new LecPlayerRequest("Caps", "Rasmus Winther", "Danimarca", PlayerRole.MID, 100, 1L,
                "/Player_immage/Mid/Caps.jpg");

        when(lecTeamRepository.findById(1L)).thenReturn(Optional.of(team));
        when(lecPlayerRepository.save(any(LecPlayer.class))).thenAnswer(inv -> {
            LecPlayer p = inv.getArgument(0);
            p.setId(10L);
            return p;
        });

        LecPlayerResponse response = lecPlayerService.create(request);

        assertThat(response.nickname()).isEqualTo("Caps");
        assertThat(response.ruolo()).isEqualTo("MID");
        assertThat(response.teamNome()).isEqualTo("G2 Esports");
        assertThat(response.imageUrl()).isEqualTo("/Player_immage/Mid/Caps.jpg");
    }

    @Test
    void lanciaEccezioneSeIlTeamNonEsiste() {
        LecPlayerRequest request = new LecPlayerRequest("Caps", null, null, PlayerRole.MID, 100, 99L, null);
        when(lecTeamRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> lecPlayerService.create(request))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    void filtraIGiocatoriPerRuolo() {
        LecPlayer support = LecPlayer.builder().id(1L).nickname("Labrov").ruolo(PlayerRole.SUPPORT).quotazione(80)
                .team(LecTeam.builder().id(1L).nome("G2 Esports").build()).build();
        when(lecPlayerRepository.findByRuolo(PlayerRole.SUPPORT)).thenReturn(java.util.List.of(support));

        var result = lecPlayerService.findAll(PlayerRole.SUPPORT, null);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).nickname()).isEqualTo("Labrov");
    }
}
