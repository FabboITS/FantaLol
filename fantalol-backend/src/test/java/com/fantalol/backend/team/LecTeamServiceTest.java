package com.fantalol.backend.team;

import com.fantalol.backend.common.BusinessRuleException;
import com.fantalol.backend.common.ResourceNotFoundException;
import com.fantalol.backend.team.dto.LecTeamRequest;
import com.fantalol.backend.team.dto.LecTeamResponse;
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
class LecTeamServiceTest {

    @Mock
    private LecTeamRepository lecTeamRepository;

    @InjectMocks
    private LecTeamService lecTeamService;

    @Test
    void creaUnNuovoTeamLecCorrettamente() {
        LecTeamRequest request = new LecTeamRequest("Team Vitality", "VIT", null);
        when(lecTeamRepository.existsByNomeIgnoreCase("Team Vitality")).thenReturn(false);
        when(lecTeamRepository.save(any(LecTeam.class))).thenAnswer(inv -> {
            LecTeam t = inv.getArgument(0);
            t.setId(1L);
            return t;
        });

        LecTeamResponse response = lecTeamService.create(request);

        assertThat(response.nome()).isEqualTo("Team Vitality");
        assertThat(response.sigla()).isEqualTo("VIT");
    }

    @Test
    void lanciaEccezioneSeIlTeamEsisteGia() {
        LecTeamRequest request = new LecTeamRequest("G2 Esports", "G2", null);
        when(lecTeamRepository.existsByNomeIgnoreCase("G2 Esports")).thenReturn(true);

        assertThatThrownBy(() -> lecTeamService.create(request))
                .isInstanceOf(BusinessRuleException.class)
                .hasMessageContaining("Esiste già");
    }

    @Test
    void lanciaEccezioneSeIlTeamNonEsiste() {
        when(lecTeamRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> lecTeamService.findById(99L))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    void eliminaUnTeamEsistente() {
        LecTeam team = LecTeam.builder().id(1L).nome("Fnatic").build();
        when(lecTeamRepository.findById(1L)).thenReturn(Optional.of(team));

        lecTeamService.delete(1L);

        verify(lecTeamRepository).delete(team);
    }
}
