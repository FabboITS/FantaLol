package com.fantalol.backend.common;

/**
 * Eccezione lanciata quando una richiesta viola una regola di business
 * (es. crediti insufficienti per l'asta, formazione non valida, ruolo mancante...).
 */
public class BusinessRuleException extends RuntimeException {

    public BusinessRuleException(String message) {
        super(message);
    }
}
