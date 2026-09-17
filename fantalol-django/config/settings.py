"""Impostazioni Django per il backend FantaLoL.

Porting delle configurazioni Spring Boot (`application.yml`) sul nuovo stack
Python/Django. Ogni valore resta pilotabile da variabile d'ambiente come nel
setup precedente.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-secret-key")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "*")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "core",
    "accounts",
    "teams",
    "leagues",
    "lineups",
    "matchdays",
    "scoring",
    "ingest",
    "worlds",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database -------------------------------------------------------------
# Postgres in produzione (come da piano di migrazione); SQLite resta il
# fallback per i test locali quando non è configurato alcun host.
if os.environ.get("DB_HOST") or os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "fantalol"),
            "USER": os.environ.get("DB_USER", "fantalol"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "fantalol"),
            "HOST": os.environ.get("DB_HOST", "db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
]

# Le password legacy sono BCrypt "puro" (Spring Security `BCryptPasswordEncoder`).
# `BCryptPasswordHasher` è l'unico hasher Django compatibile con quegli hash
# (`BCryptSHA256PasswordHasher` pre-digerisce con SHA-256 e non lo sarebbe),
# quindi resta primo in lista: gli account importati dal vecchio DB continuano
# ad autenticarsi, e le nuove password vengono scritte nello stesso formato.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "it-it"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [p for p in [BASE_DIR / "static"] if p.exists()]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(milliseconds=env_int("JWT_EXPIRATION_MS", 86_400_000)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 7)),
    "SIGNING_KEY": os.environ.get("JWT_SECRET", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.FantaLolTokenObtainPairSerializer",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FantaLoL API",
    "DESCRIPTION": (
        "API del fantasy game FantaLoL: leghe stagionali LEC/LPL/LCK e modalità Worlds. "
        "I dati di gioco provengono da PandaScore e da Leaguepedia (CC BY-SA 3.0)."
    ),
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api",
}

# --- Celery ---------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", os.environ.get("REDIS_URL", "redis://redis:6379/0"))
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = "UTC"

# --- Regole di gioco FantaLoL --------------------------------------------
FANTALOL = {
    # Fuso in cui viene valutata la finestra formazione (martedì -> giovedì).
    "LINEUP_TIMEZONE": os.environ.get("LINEUP_TIMEZONE", "Europe/Rome"),
    # Crediti iniziali di default per una lega stagionale.
    "DEFAULT_LEAGUE_CREDITS": env_int("DEFAULT_LEAGUE_CREDITS", 1000),
    # Numero massimo di FantaTeam per lega stagionale.
    "MAX_TEAMS_PER_LEAGUE": env_int("MAX_TEAMS_PER_LEAGUE", 10),
    # Durata (secondi) del countdown d'asta, riarmato a ogni rilancio.
    "AUCTION_SECONDS_PER_BID": env_int("AUCTION_SECONDS_PER_BID", 15),
    # Inizio dello split corrente: le formazioni storiche partono da qui.
    "SPLIT_BACKFILL_FROM": os.environ.get("SPLIT_BACKFILL_FROM", "2026-07-24T00:00:00+02:00"),
}

LINEUP_TIMEZONE = ZoneInfo(FANTALOL["LINEUP_TIMEZONE"])

# --- Integrazioni esterne -------------------------------------------------
PANDASCORE = {
    "API_BASE": os.environ.get("PANDASCORE_API_BASE", "https://api.pandascore.co"),
    "API_TOKEN": os.environ.get("PANDASCORE_API_TOKEN", ""),
    "TIMEOUT_SECONDS": env_int("PANDASCORE_TIMEOUT_SECONDS", 20),
    "PER_PAGE": env_int("PANDASCORE_PER_PAGE", 100),
}

LEAGUEPEDIA = {
    "API_BASE": os.environ.get("LEAGUEPEDIA_API_BASE", "https://lol.fandom.com"),
    "BOT_USERNAME": os.environ.get("LEAGUEPEDIA_BOT_USERNAME", ""),
    "BOT_PASSWORD": os.environ.get("LEAGUEPEDIA_BOT_PASSWORD", ""),
    "TIMEOUT_SECONDS": env_int("LEAGUEPEDIA_TIMEOUT_SECONDS", 20),
    # Self-throttling: almeno questo intervallo fra due richieste Cargo.
    "MIN_REQUEST_INTERVAL_SECONDS": float(os.environ.get("LEAGUEPEDIA_MIN_INTERVAL", "1.0")),
    "ENRICH_BATCH_SIZE": env_int("LEAGUEPEDIA_ENRICH_BATCH_SIZE", 10),
    "GIVE_UP_AFTER_DAYS": env_int("LEAGUEPEDIA_GIVE_UP_AFTER_DAYS", 7),
    "ATTRIBUTION": (
        "Dati dei box score forniti da Leaguepedia (lol.fandom.com), "
        "disponibili con licenza CC BY-SA 3.0."
    ),
}

# Allowlist delle leghe pro sincronizzate da PandaScore.
# Formato: "CODICE:pandascore_league_id", separati da virgola. Nessun id è
# hardcoded nel client: le leghe Worlds si aggiungono qui via env.
SUPPORTED_PRO_LEAGUES = os.environ.get("SUPPORTED_PRO_LEAGUES", "LEC:4198,LPL:294,LCK:293")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
