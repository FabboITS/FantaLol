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
-- Account amministratore. La password è conservata soltanto come hash BCrypt.
-- -------------------------------------------------------------------------
INSERT INTO users (username, email, password, role, enabled, created_at) VALUES
('Natsu_Admin', 'natsu-admin@fantalol.local', '$2y$12$5Cy4nTyT/1FSRnVVlFjgvuczPqt1Dj/6OtWCMkGTRLzuOyRvsYUTq', 'ADMIN', TRUE, NOW());

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

UPDATE lec_teams SET logo_url = CASE nome
WHEN 'Team Vitality' THEN '/assets/team-logos/team-vitality.ico'
WHEN 'Karmine Corp' THEN '/assets/team-logos/karmine-corp.png'
WHEN 'G2 Esports' THEN '/assets/team-logos/g2-esports.png'
WHEN 'Movistar KOI' THEN '/assets/team-logos/movistar-koi.png'
WHEN 'Natus Vincere' THEN '/assets/team-logos/natus-vincere.ico'
WHEN 'GIANTX' THEN '/assets/team-logos/giantx.svg'
WHEN 'Fnatic' THEN '/assets/team-logos/fnatic.png'
WHEN 'SK Gaming' THEN '/assets/team-logos/sk-gaming.ico'
WHEN 'Shifters' THEN '/assets/team-logos/shifters.ico'
WHEN 'Team Heretics' THEN '/assets/team-logos/team-heretics.png'
END;

-- -------------------------------------------------------------------------
-- Roster reali (Spring Split 2026) - 5 player per team (TOP, JUNGLE, MID, ADC, SUPPORT)
-- -------------------------------------------------------------------------

-- Team Vitality
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Naak Nako', NULL, 'Turchia', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
('Lyncas', NULL, 'Lituania', 'JUNGLE', 50, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
('FIESTA', NULL, 'Corea del Sud', 'MID', 75, (SELECT id FROM lec_teams WHERE nome = 'Team Vitality')),
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
('SamD', NULL, 'Corea del Sud', 'ADC', 55, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere')),
('Parus', NULL, 'Turchia', 'SUPPORT', 50, (SELECT id FROM lec_teams WHERE nome = 'Natus Vincere'));

-- GIANTX
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Oscarinin', NULL, 'Spagna', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Isma', NULL, 'Francia', 'JUNGLE', 55, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Jackies', NULL, 'Repubblica Ceca', 'MID', 60, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Flakked', NULL, 'Spagna', 'ADC', 60, (SELECT id FROM lec_teams WHERE nome = 'GIANTX')),
('Jun', NULL, 'Corea del Sud', 'SUPPORT', 55, (SELECT id FROM lec_teams WHERE nome = 'GIANTX'));

-- Fnatic
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Soboro', NULL, 'Corea del Sud', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Razork', NULL, 'Spagna', 'JUNGLE', 75, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Vladi', NULL, 'Grecia', 'MID', 70, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Upset', NULL, 'Germania', 'ADC', 80, (SELECT id FROM lec_teams WHERE nome = 'Fnatic')),
('Lospa', NULL, 'Corea del Sud', 'SUPPORT', 60, (SELECT id FROM lec_teams WHERE nome = 'Fnatic'));

-- SK Gaming
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Wunder', NULL, 'Danimarca', 'TOP', 65, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('Skeanz', NULL, 'Francia', 'JUNGLE', 55, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('SlowQ', NULL, 'Corea del Sud', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('Jopa', NULL, 'Croazia', 'ADC', 50, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming')),
('Mikyx', NULL, 'Slovenia', 'SUPPORT', 75, (SELECT id FROM lec_teams WHERE nome = 'SK Gaming'));

-- Shifters
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Rooster', NULL, 'Corea del Sud', 'TOP', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('Sheo', NULL, 'Francia', 'JUNGLE', 60, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('nuc', NULL, 'Marocco/Francia', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('Paduck', NULL, 'Corea del Sud', 'ADC', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters')),
('Stend', NULL, 'Francia', 'SUPPORT', 55, (SELECT id FROM lec_teams WHERE nome = 'Shifters'));

-- Team Heretics
INSERT INTO lec_players (nickname, nome_reale, nazionalita, ruolo, quotazione, team_id) VALUES
('Tracyn', NULL, 'Polonia', 'TOP', 50, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Daglas', NULL, 'Polonia', 'JUNGLE', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Serin', NULL, 'Turchia', 'MID', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Hype', NULL, 'Corea del Sud', 'ADC', 55, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics')),
('Way', NULL, 'Corea del Sud', 'SUPPORT', 60, (SELECT id FROM lec_teams WHERE nome = 'Team Heretics'));

-- Ritratti locali serviti dal frontend
UPDATE lec_players SET image_url = CASE nickname
WHEN 'Naak Nako' THEN '/Player_immage/Top/Naak_Nako.jpg'
WHEN 'Lyncas' THEN '/Player_immage/Jungle/Lyncas.jpg'
WHEN 'FIESTA' THEN '/Player_immage/Mid/FIESTA.jpg'
WHEN 'Carzzy' THEN '/Player_immage/Adc/Carzzy.jpg'
WHEN 'Fleshy' THEN '/Player_immage/Support/Fleshy.jpg'
WHEN 'Canna' THEN '/Player_immage/Top/Canna.jpg'
WHEN 'Yike' THEN '/Player_immage/Jungle/Yike.jpg'
WHEN 'Kyeahoo' THEN '/Player_immage/Mid/Kyeahoo.jpg'
WHEN 'Caliste' THEN '/Player_immage/Adc/Caliste.jpg'
WHEN 'Busio' THEN '/Player_immage/Support/Busio.jpg'
WHEN 'BrokenBlade' THEN '/Player_immage/Top/BrokenBlade.jpg'
WHEN 'SkewMond' THEN '/Player_immage/Jungle/SkewMond.jpg'
WHEN 'Caps' THEN '/Player_immage/Mid/Caps.jpg'
WHEN 'Hans Sama' THEN '/Player_immage/Adc/Hans_Sama.jpg'
WHEN 'Labrov' THEN '/Player_immage/Support/Labrov.jpg'
WHEN 'Myrwn' THEN '/Player_immage/Top/Myrwn.jpg'
WHEN 'Elyoya' THEN '/Player_immage/Jungle/Elyoya.jpg'
WHEN 'Jojopyun' THEN '/Player_immage/Mid/Jojopyun.jpg'
WHEN 'Supa' THEN '/Player_immage/Adc/Supa.jpg'
WHEN 'Alvaro' THEN '/Player_immage/Support/Alvaro.jpg'
WHEN 'Maynter' THEN '/Player_immage/Top/Maynter.jpg'
WHEN 'Rhilech' THEN '/Player_immage/Jungle/Rhilech.jpg'
WHEN 'Poby' THEN '/Player_immage/Mid/Poby.jpg'
WHEN 'SamD' THEN '/Player_immage/Adc/SamD.jpg'
WHEN 'Parus' THEN '/Player_immage/Support/Parus.jpg'
WHEN 'Oscarinin' THEN '/Player_immage/Top/Oscarinin.jpg'
WHEN 'Isma' THEN '/Player_immage/Jungle/ISMA.jpg'
WHEN 'Jackies' THEN '/Player_immage/Mid/Jackies.jpg'
WHEN 'Flakked' THEN '/Player_immage/Adc/Flakked.jpg'
WHEN 'Jun' THEN '/Player_immage/Support/Jun.jpg'
WHEN 'Soboro' THEN '/Player_immage/Top/Soboro.jpg'
WHEN 'Razork' THEN '/Player_immage/Jungle/Razork.jpg'
WHEN 'Vladi' THEN '/Player_immage/Mid/Vladi.jpg'
WHEN 'Upset' THEN '/Player_immage/Adc/Upset.jpg'
WHEN 'Lospa' THEN '/Player_immage/Support/Lospa.jpg'
WHEN 'Wunder' THEN '/Player_immage/Top/Wunder.jpg'
WHEN 'Skeanz' THEN '/Player_immage/Jungle/Skeanz.jpg'
WHEN 'SlowQ' THEN '/Player_immage/Mid/SlowQ.jpg'
WHEN 'Jopa' THEN '/Player_immage/Adc/Jopa.jpg'
WHEN 'Mikyx' THEN '/Player_immage/Support/Mikyx.jpg'
WHEN 'Rooster' THEN '/Player_immage/Top/Rooster.jpg'
WHEN 'Sheo' THEN '/Player_immage/Jungle/Sheo.jpg'
WHEN 'nuc' THEN '/Player_immage/Mid/nuc.jpg'
WHEN 'Paduck' THEN '/Player_immage/Adc/Paduck.jpg'
WHEN 'Stend' THEN '/Player_immage/Support/Stend.jpg'
WHEN 'Tracyn' THEN '/Player_immage/Top/Tracyn.jpg'
WHEN 'Daglas' THEN '/Player_immage/Jungle/Daglas.jpg'
WHEN 'Serin' THEN '/Player_immage/Mid/Serin.jpg'
WHEN 'Hype' THEN '/Player_immage/Adc/Hype.jpg'
WHEN 'Way' THEN '/Player_immage/Support/Way.jpg'
END;

-- -------------------------------------------------------------------------
-- Una lega demo con codice invito fisso, utile per i test da Postman
-- -------------------------------------------------------------------------
INSERT INTO leagues (nome, codice_invito, crediti_iniziali, admin_id, created_at)
VALUES ('Lega Demo Postman', 'DEMO1234', 1000, (SELECT id FROM users WHERE username = 'Natsu_Admin'), NOW());

-- -------------------------------------------------------------------------
-- Una prima giornata di campionato, pronta per l'inserimento statistiche
-- -------------------------------------------------------------------------
INSERT INTO matchdays (league_id, numero, descrizione, data, chiusa)
VALUES ((SELECT id FROM leagues WHERE codice_invito = 'DEMO1234'), 1, 'Spring Split 2026 - Week 1', CURDATE(), FALSE);
