"""Dati di seed portati da `config/DataSeeder.java` (roster LEC Summer 2026).

I valori — nickname, ruolo, nazionalità e quotazione base — sono ripresi tali e
quali dal seeder Java: nessuna quotazione è stata ricalcolata.

I roster LPL e LCK **non** sono presenti nel repository Java e non vengono
inventati qui: si importano da PandaScore con

    python manage.py import_pro_rosters --competition LPL

oppure si caricano da un JSON con la stessa forma di `LEC_TEAMS`
(`python manage.py seed_base_data --rosters percorso/rosters.json`).
"""
from __future__ import annotations

TEAM_LOGOS = {
    "Team Vitality": "/assets/team-logos/team-vitality.ico",
    "Karmine Corp": "/assets/team-logos/karmine-corp.png",
    "G2 Esports": "/assets/team-logos/g2-esports.png",
    "Movistar KOI": "/assets/team-logos/movistar-koi.png",
    "Natus Vincere": "/assets/team-logos/natus-vincere.ico",
    "GIANTX": "/assets/team-logos/giantx.svg",
    "Fnatic": "/assets/team-logos/fnatic.png",
    "SK Gaming": "/assets/team-logos/sk-gaming.ico",
    "Shifters": "/assets/team-logos/shifters.ico",
    "Team Heretics": "/assets/team-logos/team-heretics.png",
}

ROLE_FOLDERS = {"TOP": "Top", "JUNGLE": "Jungle", "MID": "Mid", "ADC": "Adc", "SUPPORT": "Support"}

#: Nickname con nome file immagine diverso dal nickname stesso.
IMAGE_FILENAME_OVERRIDES = {"Naak Nako": "Naak_Nako", "Hans Sama": "Hans_Sama", "Isma": "ISMA"}

# (nome, sigla, [(nickname, ruolo, nazionalità, quotazione), ...])
LEC_TEAMS = [
    ("Team Vitality", "VIT", [
        ("Naak Nako", "TOP", "Turchia", 55),
        ("Lyncas", "JUNGLE", "Lituania", 50),
        ("FIESTA", "MID", "Corea del Sud", 75),
        ("Carzzy", "ADC", "Danimarca", 80),
        ("Fleshy", "SUPPORT", "Turchia", 55),
    ]),
    ("Karmine Corp", "KC", [
        ("Canna", "TOP", "Corea del Sud", 90),
        ("Yike", "JUNGLE", "Danimarca", 80),
        ("Kyeahoo", "MID", "Corea del Sud", 65),
        ("Caliste", "ADC", "Francia", 85),
        ("Busio", "SUPPORT", "Stati Uniti", 80),
    ]),
    ("G2 Esports", "G2", [
        ("BrokenBlade", "TOP", "Germania/Turchia", 85),
        ("SkewMond", "JUNGLE", "Francia/Libano", 80),
        ("Caps", "MID", "Danimarca", 100),
        ("Hans Sama", "ADC", "Francia", 90),
        ("Labrov", "SUPPORT", "Grecia", 80),
    ]),
    ("Movistar KOI", "MKOI", [
        ("Myrwn", "TOP", "Spagna", 65),
        ("Elyoya", "JUNGLE", "Spagna", 95),
        ("Jojopyun", "MID", "Stati Uniti", 85),
        ("Supa", "ADC", "Spagna", 70),
        ("Alvaro", "SUPPORT", "Spagna", 75),
    ]),
    ("Natus Vincere", "NAVI", [
        ("Maynter", "TOP", "Ucraina", 55),
        ("Rhilech", "JUNGLE", "Turchia", 60),
        ("Poby", "MID", "Corea del Sud", 55),
        ("SamD", "ADC", "Corea del Sud", 55),
        ("Parus", "SUPPORT", "Turchia", 50),
    ]),
    ("GIANTX", "GX", [
        ("Oscarinin", "TOP", "Spagna", 55),
        ("Isma", "JUNGLE", "Francia", 55),
        ("Jackies", "MID", "Repubblica Ceca", 60),
        ("Flakked", "ADC", "Spagna", 60),
        ("Jun", "SUPPORT", "Corea del Sud", 55),
    ]),
    ("Fnatic", "FNC", [
        ("Soboro", "TOP", "Corea del Sud", 55),
        ("Razork", "JUNGLE", "Spagna", 75),
        ("Vladi", "MID", "Grecia", 70),
        ("Upset", "ADC", "Germania", 80),
        ("Lospa", "SUPPORT", "Corea del Sud", 60),
    ]),
    ("SK Gaming", "SK", [
        ("Wunder", "TOP", "Danimarca", 65),
        ("Skeanz", "JUNGLE", "Francia", 55),
        ("SlowQ", "MID", "Corea del Sud", 55),
        ("Jopa", "ADC", "Croazia", 50),
        ("Mikyx", "SUPPORT", "Slovenia", 75),
    ]),
    ("Shifters", "SHFT", [
        ("Rooster", "TOP", "Corea del Sud", 55),
        ("Sheo", "JUNGLE", "Francia", 60),
        ("nuc", "MID", "Marocco/Francia", 55),
        ("Paduck", "ADC", "Corea del Sud", 55),
        ("Stend", "SUPPORT", "Francia", 55),
    ]),
    ("Team Heretics", "TH", [
        ("Tracyn", "TOP", "Polonia", 50),
        ("Daglas", "JUNGLE", "Polonia", 55),
        ("Serin", "MID", "Turchia", 55),
        ("Hype", "ADC", "Corea del Sud", 55),
        ("Way", "SUPPORT", "Corea del Sud", 60),
    ]),
]


def player_image_url(nickname: str, ruolo: str) -> str:
    folder = ROLE_FOLDERS[ruolo]
    filename = IMAGE_FILENAME_OVERRIDES.get(nickname, nickname)
    return f"/Player_immage/{folder}/{filename}.jpg"


def team_logo_url(nome: str) -> str | None:
    return TEAM_LOGOS.get(nome)
