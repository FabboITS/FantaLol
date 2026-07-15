-- =========================================================================
-- Fanta LoL - Script di creazione della struttura del database (DDL)
-- Compatibile con MySQL 8.0
--
-- Nota: quando l'applicazione viene avviata con Spring Boot, Hibernate
-- (spring.jpa.hibernate.ddl-auto=update) crea/aggiorna automaticamente lo
-- schema in base alle entità JPA. Questo script è fornito come deliverable
-- standalone, utile per ispezionare la struttura del database indipendentemente
-- dall'applicazione o per un setup manuale.
-- =========================================================================

CREATE DATABASE IF NOT EXISTS fantalol CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fantalol;

-- -------------------------------------------------------------------------
-- Modulo Utenti
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS user_profiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    nome_visualizzato VARCHAR(60),
    bio VARCHAR(255),
    avatar_url VARCHAR(255),
    summoner_name VARCHAR(60),
    user_id BIGINT NOT NULL UNIQUE,
    CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- -------------------------------------------------------------------------
-- Modulo Team/Player LEC
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lec_teams (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(80) NOT NULL UNIQUE,
    sigla VARCHAR(10),
    logo_url VARCHAR(255)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS lec_players (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    nickname VARCHAR(60) NOT NULL,
    nome_reale VARCHAR(120),
    nazionalita VARCHAR(60),
    image_url VARCHAR(255),
    ruolo VARCHAR(20) NOT NULL,
    quotazione INT NOT NULL,
    team_id BIGINT NOT NULL,
    CONSTRAINT fk_player_team FOREIGN KEY (team_id) REFERENCES lec_teams (id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- -------------------------------------------------------------------------
-- Modulo Leghe / Asta / Rose
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leagues (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    codice_invito VARCHAR(12) NOT NULL UNIQUE,
    crediti_iniziali INT NOT NULL,
    admin_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_league_admin FOREIGN KEY (admin_id) REFERENCES users (id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS fanta_teams (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(80) NOT NULL,
    crediti_residui INT NOT NULL,
    league_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    CONSTRAINT fk_fantateam_league FOREIGN KEY (league_id) REFERENCES leagues (id) ON DELETE CASCADE,
    CONSTRAINT fk_fantateam_owner FOREIGN KEY (owner_id) REFERENCES users (id),
    CONSTRAINT uq_fantateam_league_owner UNIQUE (league_id, owner_id)
) ENGINE = InnoDB;

-- Classe associativa: relazione ManyToMany FantaTeam <-> LecPlayer arricchita con attributi propri
CREATE TABLE IF NOT EXISTS roster_entries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    fanta_team_id BIGINT NOT NULL,
    lec_player_id BIGINT NOT NULL,
    crediti_spesi INT NOT NULL,
    data_acquisto DATETIME(6) NOT NULL,
    CONSTRAINT fk_roster_fantateam FOREIGN KEY (fanta_team_id) REFERENCES fanta_teams (id) ON DELETE CASCADE,
    CONSTRAINT fk_roster_player FOREIGN KEY (lec_player_id) REFERENCES lec_players (id),
    CONSTRAINT uq_roster_fantateam_player UNIQUE (fanta_team_id, lec_player_id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS auction_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    league_id BIGINT NOT NULL,
    lec_player_id BIGINT NOT NULL,
    highest_bidder_id BIGINT,
    current_bid INT NOT NULL,
    ends_at DATETIME(6) NOT NULL,
    status VARCHAR(20) NOT NULL,
    CONSTRAINT fk_auction_league FOREIGN KEY (league_id) REFERENCES leagues (id) ON DELETE CASCADE,
    CONSTRAINT fk_auction_player FOREIGN KEY (lec_player_id) REFERENCES lec_players (id),
    CONSTRAINT fk_auction_bidder FOREIGN KEY (highest_bidder_id) REFERENCES fanta_teams (id) ON DELETE SET NULL
) ENGINE = InnoDB;

-- -------------------------------------------------------------------------
-- Modulo Giornate / Statistiche / Formazioni
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS matchdays (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    league_id BIGINT NOT NULL,
    numero INT NOT NULL,
    descrizione VARCHAR(100),
    data DATE,
    chiusa BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_matchday_league FOREIGN KEY (league_id) REFERENCES leagues (id) ON DELETE CASCADE,
    CONSTRAINT uq_matchday_league_numero UNIQUE (league_id, numero)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS player_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    matchday_id BIGINT NOT NULL,
    lec_player_id BIGINT NOT NULL,
    voto_base DOUBLE NOT NULL,
    kills INT NOT NULL DEFAULT 0,
    morti INT NOT NULL DEFAULT 0,
    assist INT NOT NULL DEFAULT 0,
    mvp BOOLEAN NOT NULL DEFAULT FALSE,
    vittoria BOOLEAN NOT NULL DEFAULT FALSE,
    fantavoto DOUBLE NOT NULL,
    CONSTRAINT fk_stat_matchday FOREIGN KEY (matchday_id) REFERENCES matchdays (id) ON DELETE CASCADE,
    CONSTRAINT fk_stat_player FOREIGN KEY (lec_player_id) REFERENCES lec_players (id),
    CONSTRAINT uq_stat_matchday_player UNIQUE (matchday_id, lec_player_id)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS formations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    fanta_team_id BIGINT NOT NULL,
    matchday_id BIGINT NOT NULL,
    capitano_id BIGINT,
    punteggio_totale DOUBLE,
    CONSTRAINT fk_formation_fantateam FOREIGN KEY (fanta_team_id) REFERENCES fanta_teams (id) ON DELETE CASCADE,
    CONSTRAINT fk_formation_matchday FOREIGN KEY (matchday_id) REFERENCES matchdays (id) ON DELETE CASCADE,
    CONSTRAINT fk_formation_capitano FOREIGN KEY (capitano_id) REFERENCES lec_players (id),
    CONSTRAINT uq_formation_team_matchday UNIQUE (fanta_team_id, matchday_id)
) ENGINE = InnoDB;

-- Relazione ManyToMany "semplice" Formation <-> LecPlayer (titolari schierati)
CREATE TABLE IF NOT EXISTS formation_titolari (
    formation_id BIGINT NOT NULL,
    lec_player_id BIGINT NOT NULL,
    PRIMARY KEY (formation_id, lec_player_id),
    CONSTRAINT fk_formtitolari_formation FOREIGN KEY (formation_id) REFERENCES formations (id) ON DELETE CASCADE,
    CONSTRAINT fk_formtitolari_player FOREIGN KEY (lec_player_id) REFERENCES lec_players (id)
) ENGINE = InnoDB;
