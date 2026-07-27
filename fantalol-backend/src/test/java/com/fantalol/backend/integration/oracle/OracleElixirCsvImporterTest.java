package com.fantalol.backend.integration.oracle;

import com.fantalol.backend.matchday.*;
import com.fantalol.backend.team.LecPlayer;
import com.fantalol.backend.team.LecPlayerRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OracleElixirCsvImporterTest {
    @Mock MatchdayRepository matchdayRepository;
    @Mock PlayerStatRepository playerStatRepository;
    @Mock ImportedGameRepository importedGameRepository;
    @Mock LecPlayerRepository lecPlayerRepository;
    @Mock FantaScoreCalculator scoreCalculator;
    @InjectMocks OracleElixirCsvImporter importer;

    @Test
    void importsCompleteLecRowsAndSkipsDuplicateGames() {
        Matchday matchday = Matchday.builder().id(4L).numero(1).build();
        LecPlayer player = LecPlayer.builder().id(7L).nickname("Caps").build();
        String csv = "gameid,league,split,datacompleteness,position,playerid,playername,champion,kills,deaths,assists,total cs,visionscore,result\n"
                + "GAME-1,LEC,Spring,complete,mid,oe-caps,Caps,Ahri,4,1,7,245,31,1\n";

        when(matchdayRepository.findById(4L)).thenReturn(Optional.of(matchday));
        when(importedGameRepository.existsByProviderAndExternalGameId("ORACLES_ELIXIR", "GAME-1"))
                .thenReturn(false);
        when(lecPlayerRepository.findByOraclePlayerId("oe-caps")).thenReturn(Optional.of(player));
        when(playerStatRepository.findByMatchdayIdAndLecPlayerId(4L, 7L)).thenReturn(Optional.empty());
        when(scoreCalculator.calculate(any(PlayerStat.class))).thenReturn(26.0);

        OracleImportResult result = importer.importCsv(4L,
                new MockMultipartFile("file", "data.csv", "text/csv", csv.getBytes()), "LEC", "Spring");

        assertThat(result.importedGames()).isEqualTo(1);
        assertThat(result.importedPlayerRows()).isEqualTo(1);
        verify(playerStatRepository).save(argThat(stat -> stat.getKills() == 4
                && stat.getMorti() == 1
                && stat.getAssist() == 7
                && stat.getCs() == 245
                && stat.getVisionScore() == 31
                && stat.getWins() == 1));
        verify(importedGameRepository).save(any(ImportedGame.class));
    }
}
