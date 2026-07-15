package com.fantalol.backend.matchday;

import org.springframework.stereotype.Component;

/**
 * Calcola il "fantavoto" di un player LEC in una giornata, a partire dal voto base
 * e dai bonus/malus statistici, secondo regole ispirate al Fantacalcio classico ma
 * adattate al competitivo di League of Legends.
 * <p>
 * Formula:
 * <pre>
 * fantavoto = votoBase
 *           + (kills   * BONUS_KILL)
 *           + (assist  * BONUS_ASSIST)
 *           - (morti   * MALUS_MORTE)
 *           + (mvp     ? BONUS_MVP     : 0)
 *           + (vittoria ? BONUS_VITTORIA : 0)
 * </pre>
 */
@Component
public class FantaScoreCalculator {

    public static final double BONUS_KILL = 0.5;
    public static final double BONUS_ASSIST = 0.3;
    public static final double MALUS_MORTE = 0.4;
    public static final double BONUS_MVP = 2.0;
    public static final double BONUS_VITTORIA = 1.0;

    public double calcola(double votoBase, int kills, int morti, int assist, boolean mvp, boolean vittoria) {
        double fantavoto = votoBase
                + (kills * BONUS_KILL)
                + (assist * BONUS_ASSIST)
                - (morti * MALUS_MORTE)
                + (mvp ? BONUS_MVP : 0)
                + (vittoria ? BONUS_VITTORIA : 0);

        // Il fantavoto non può scendere sotto lo zero.
        return Math.max(fantavoto, 0.0);
    }

    public double calcola(PlayerStat stat) {
        return calcola(stat.getVotoBase(), stat.getKills(), stat.getMorti(), stat.getAssist(),
                stat.isMvp(), stat.isVittoria());
    }
}
