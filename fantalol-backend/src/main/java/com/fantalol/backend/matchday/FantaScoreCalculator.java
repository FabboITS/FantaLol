package com.fantalol.backend.matchday;

import org.springframework.stereotype.Component;

/** Calcola il punteggio ufficiale descritto in Rules.md. */
@Component
public class FantaScoreCalculator {
    public double calcola(int kills, int morti, int assist, int cs, boolean vittoria) {
        return kills * 3.0
                + assist * 2.0
                - morti * 2.0
                + Math.floorDiv(cs, 100)
                + (vittoria ? 3.0 : 0.0);
    }

    public double calcola(PlayerStat stat) {
        return calcola(stat.getKills(), stat.getMorti(), stat.getAssist(), stat.getCs(), stat.isVittoria());
    }
}
