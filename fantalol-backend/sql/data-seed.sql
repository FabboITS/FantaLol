-- =========================================================================
-- Fanta LoL - Script di popolamento (seed) del database
-- Da eseguire DOPO 'schema.sql'. Compatibile con MySQL 8.0.
--
-- Nota: l'applicazione esegue comunque un seed automatico all'avvio tramite
-- DataSeeder (CommandLineRunner) se il database è vuoto. Questo script è
-- fornito come deliverable standalone per popolare il DB indipendentemente
-- dall'applicazione (es. per ispezione diretta o demo rapide).
-- =========================================================================

USE fantalol;

-- -------------------------------------------------------------------------
-- Utenti demo
-- Password in chiaro per riferimento (hash BCrypt sotto):
--   admin      -> Admin123!
--   mago       -> Password123!
--   silva      -> Password123!
-- -------------------------------------------------------------------------
INSERT INTO users (username, email, password, role, enabled, created_at) VALUES
('admin', 'admin@fantalol.local', '$2b$10$fqE.Eik8Ff.cqvip0sbGneft8oxi2CTPMeckjlKBJHgO6q.2UAAoC', 'ADMIN', TRUE, NOW()),
('mago',  'mago@fantalol.it',     '$2b$10$9f6mZ1fUUnQTjWnBfvLC2.6NvUC4dj38.uV1mg1YWHKvbQYsNyXHi', 'USER',  TRUE, NOW()),
('silva', 'silva@fantalol.it',    '$2b$10$9f6mZ1fUUnQTjWnBfvLC2.6NvUC4dj38.uV1mg1YWHKvbQYsNyXHi', 'USER',  TRUE, NOW());

-- -------------------------------------------------------------------------
-- I 10 team della LEC (League of Legends EMEA Championship)
-- -------------------------------------------------------------------------
INSERT INTO lec_teams (nome, sigla) VALUES
('Team Vitality', 'VIT'),
('Karmine Corp', 'KC'),
('G2 Esports', 'G2'),
('Movistar KOI', 'MKOI'),
('Natus Vincere', 'NAVI'),
('GIANTX', 'GX'),
('Fnatic', 'FNC'),
('SK Gaming', 'SK'),
('Shifters', 'SHFT'),
('Team Heretics', 'TH');

-- -------------------------------------------------------------------------
-- Roster reali (Spring Split 2026) - 5 player per team (TOP, JUNGLE, MID, ADC, SUPPORT)
-- -------------------------------------------------------------------------

-- Team Vitality
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Naak Nako', NULL, 'Turchia', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
('Lyncas', NULL, 'Lituania', 'JUNGLE', 50, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
('Humanoid', NULL, 'Repubblica Ceca', 'MID', 75, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
('Carzzy', NULL, 'Danimarca', 'ADC', 80, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
('Fleshy', NULL, 'Turchia', 'SUPPORT', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality'));

-- Karmine Corp
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Canna', NULL, 'Corea del Sud', 'TOP', 90, (SELECT id FROM lec_teams WHERE nome = 'Karmine Corp')),
('Yike', NULL, 'Danimarca', 'JUNGLE', 80, (SELECT id FROM lec_teams WHERE nome = 'Karmine Corp')),
('Kyeahoo', NULL, 'Corea del Sud', 'MID', 65, (SELECT id FROM lec_teams WHERE nome = 'Karmine Corp')),
('Caliste', NULL, 'Francia', 'ADC', 85, (SELECT id FROM lec_teams WHERE nome = 'Karmine Corp')),
('Busio', NULL, 'Stati Uniti', 'SUPPORT', 80, (SELECT id FROM lec_teams WHERE nome = 'Karmine Corp'));

-- G2 Esports
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('BrokenBlade', NULL, 'Germania/Turchia', 'TOP', 85, (SELECT id FROM lec_teams WHERE nome = 'G2 Esports')),
('SkewMond', NULL, 'Francia/Libano', 'JUNGLE', 80, (SELECT id FROM lec_teams WHERE nome = 'G2 Esports')),
('Caps', NULL, 'Danimarca', 'MID', 100, (SELECT id FROM lec_teams WHERE nome = 'G2 Esports')),
('Hans Sama', NULL, 'Francia', 'ADC', 90, (SELECT id FROM lec_teams WHERE nome = 'G2 Esports')),
('Labrov', NULL, 'Grecia', 'SUPPORT', 80, (SELECT id FROM lec_teams WHERE nome = 'G2 Esports'));

-- Movistar KOI
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Myrwn', NULL, 'Spagna', 'TOP', 65, (SELECT id FROM lec_teams WHERE nome = 'Movistar KOI')),
('Elyoya', NULL, 'Spagna', 'JUNGLE', 95, (SELECT id FROM lec_teams WHERE nome = 'Movistar KOI')),
('Jojopyun', NULL, 'Stati Uniti', 'MID', 85, (SELECT id FROM lec_teams WHERE nome = 'Movistar KOI')),
('Supa', NULL, 'Spagna', 'ADC', 70, (SELECT id FROM lec_teams WHERE nome = 'Movistar KOI')),
('Alvaro', NULL, 'Spagna', 'SUPPORT', 75, (SELECT id FROM lec_teams WHERE nome = 'Movistar KOI'));

-- Natus Vincere
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Maynter', NULL, 'Ucraina', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere')),
('Rhilech', NULL, 'Turchia', 'JUNGLE', 60, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere')),
('Poby', NULL, 'Corea del Sud', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere')),
('Hans SamD', NULL, 'Corea del Sud', 'ADC', 55, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere')),
('Parus', NULL, 'Turchia', 'SUPPORT', 50, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere'));

-- GIANTX
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Lot', NULL, 'Turchia', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Isma', NULL, 'Francia', 'JUNGLE', 55, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Jackies', NULL, 'Repubblica Ceca', 'MID', 60, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Noah', NULL, 'Corea del Sud', 'ADC', 60, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Jun', NULL, 'Corea del Sud', 'SUPPORT', 55, (SELECT id FROM lec_teams WHERE nome = 'GIANTX'));

-- Fnatic
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Empyros', NULL, 'Grecia', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Razork', NULL, 'Spagna', 'JUNGLE', 75, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Vladi', NULL, 'Grecia', 'MID', 70, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Upset', NULL, 'Germania', 'ADC', 80, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Lospa', NULL, 'Corea del Sud', 'SUPPORT', 60, (SELECT id FROM lec_teams WHERE nome = 'Fnatic'));

-- SK Gaming
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Wunder', NULL, 'Danimarca', 'TOP', 65, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('Skeanz', NULL, 'Francia', 'JUNGLE', 55, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('LIDER', NULL, 'Norvegia', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('Jopa', NULL, 'Croazia', 'ADC', 50, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('Mikyx', NULL, 'Slovenia', 'SUPPORT', 75, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming'));

-- Shifters
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Rooster', NULL, 'Corea del Sud', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('Boukada', NULL, 'Francia', 'JUNGLE', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('nuc', NULL, 'Marocco/Francia', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('Paduck', NULL, 'Corea del Sud', 'ADC', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('Trymbi', NULL, 'Polonia', 'SUPPORT', 60, (SELECT id FROM lec_teams WHERE nome = 'Shifters'));

-- Team Heretics
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Tracyn', NULL, 'Polonia', 'TOP', 50, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Sheo', NULL, 'Francia', 'JUNGLE', 60, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Serin', NULL, 'Turchia', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Ice', NULL, 'Corea del Sud', 'ADC', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Stend', NULL, 'Francia', 'SUPPORT', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics'));

-- -------------------------------------------------------------------------
-- Una lega demo con codice invito fisso, utile per i test da Postman
-- -------------------------------------------------------------------------
INSERT INTO leagues (nome, codice_invito, crediti_iniziali, admin_id, created_at)
VALUES ('Lega Demo Postman', 'DEMO1234', 1000, (SELECT id FROM users WHERE username = 'admin'), NOW());

-- -------------------------------------------------------------------------
-- Una prima giornata di campionato, pronta per l'inserimento statistiche
-- -------------------------------------------------------------------------
INSERT INTO matchdays (league_id, numero, descrizione, data, chiusa)
VALUES ((SELECT id FROM leagues WHERE codice_invito = 'DEMO1234'), 1, 'Spring Split 2026 - Week 1', CURDATE(), FALSE);
