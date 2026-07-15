package com.fantalol.backend.common;

/**
 * Eccezione lanciata quando una risorsa richiesta (entità) non viene trovata nel database.
 */
public class ResourceNotFoundException extends RuntimeException {

    public ResourceNotFoundException(String message) {
        super(message);
    }
}
