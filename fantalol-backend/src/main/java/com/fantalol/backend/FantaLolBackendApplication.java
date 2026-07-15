package com.fantalol.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Entry point dell'applicazione Fanta LoL Backend.
 * <p>
 * Progetto realizzato per il project work finale UF14 - Java Backend.
 * Implementa un "Fanta Calcio" applicato al competitivo di League of Legends,
 * limitato ai 10 team della LEC (League of Legends EMEA Championship).
 */
@SpringBootApplication
@EnableScheduling
public class FantaLolBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(FantaLolBackendApplication.class, args);
    }
}
