"""Impostazioni comuni a tutti gli ambienti di FantaLol."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def env_int(name: str, default: int) -> int:
    value = env(name)
    return int(value) if value is not None else default


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = False
ALLOWED_HOSTS = (env("DJANGO_ALLOWED_HOSTS", "*") or "*").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in (env("DJANGO_CSRF_TRUSTED_ORIGINS", "") or "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "apps.common",
    "apps.users",
    "apps.competitions",
    "apps.esports",
    "apps.providers",
    "apps.leagues",
    "apps.lineups",
    "apps.matchdays",
    "apps.scoring",
    "apps.worlds",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.common.middleware.ApiCorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", "postgres://fantalol:fantalol@db:5432/fantalol") or "",
        conn_max_age=60,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    # Hash BCrypt importati dal backend Java (formato "bcrypt$$2a$...").
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
]

LANGUAGE_CODE = "it-it"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_DIR = Path(env("FRONTEND_DIR", str(REPO_DIR / "frontend")) or "")
WHITENOISE_ROOT = FRONTEND_DIR if FRONTEND_DIR.exists() else None
WHITENOISE_INDEX_FILE = True
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")) or "")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": [
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
    ],
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

JWT_EXPIRATION_MS = env_int("JWT_EXPIRATION_MS", 86_400_000)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(milliseconds=JWT_EXPIRATION_MS),
    "SIGNING_KEY": env("JWT_SECRET", "dev-jwt-secret-change-me-please-32-bytes!!"),
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "UPDATE_LAST_LOGIN": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FantaLol API",
    "DESCRIPTION": "API REST di FantaLol v2 (LEC · LCK · LPL · WORLDS).",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "DISABLE_ERRORS_AND_WARNINGS": True,
    "CAMELIZE_NAMES": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
    ],
}

# --- Integrazioni e regole -------------------------------------------------
PANDASCORE_API_TOKEN = env("PANDASCORE_API_TOKEN")
PANDASCORE_API_BASE = env("PANDASCORE_API_BASE", "https://api.pandascore.co")
LEAGUEPEDIA_BOT_USERNAME = env("LEAGUEPEDIA_BOT_USERNAME")
LEAGUEPEDIA_BOT_PASSWORD = env("LEAGUEPEDIA_BOT_PASSWORD")
LEAGUEPEDIA_API_BASE = env("LEAGUEPEDIA_API_BASE", "https://lol.fandom.com")
LEAGUEPEDIA_ENRICH_BATCH_SIZE = env_int("LEAGUEPEDIA_ENRICH_BATCH_SIZE", 10)
LEAGUEPEDIA_GIVE_UP_DAYS = env_int("LEAGUEPEDIA_GIVE_UP_DAYS", 7)
LEAGUEPEDIA_MIN_INTERVAL_SECONDS = float(env("LEAGUEPEDIA_MIN_INTERVAL_SECONDS", "1.0") or 1.0)
ESPORTS_STALE_AFTER_MINUTES = env_int("ESPORTS_STALE_AFTER_MINUTES", 90)
AUCTION_SECONDS_PER_BID = env_int("AUCTION_SECONDS_PER_BID", 15)
CREDITI_INIZIALI_DEFAULT = env_int("CREDITI_INIZIALI_DEFAULT", 1000)
REGIONAL_DEFAULT_QUOTAZIONE = env_int("REGIONAL_DEFAULT_QUOTAZIONE", 10)
HTTP_TIMEOUT_SECONDS = float(env("HTTP_TIMEOUT_SECONDS", "20") or 20)

ADMIN_USERNAME = env("ADMIN_USERNAME")
ADMIN_EMAIL = env("ADMIN_EMAIL")
ADMIN_PASSWORD = env("ADMIN_PASSWORD")

LEAGUEPEDIA_ATTRIBUTION = (
    "Statistiche delle partite da Leaguepedia (lol.fandom.com), "
    "contenuti disponibili con licenza CC BY-SA 3.0."
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps": {"level": env("FANTALOL_LOG_LEVEL", "INFO"), "propagate": True},
        "httpx": {"level": "WARNING"},
        "apscheduler": {"level": "WARNING"},
    },
}
