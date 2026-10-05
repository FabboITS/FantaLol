from .base import *  # noqa: F401,F403
from .base import env

DATABASES["default"] = __import__("dj_database_url").parse(  # noqa: F405
    env("DATABASE_URL", "postgres://fantalol:fantalol@localhost:5432/fantalol") or ""
)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher", *PASSWORD_HASHERS]  # noqa: F405
LEAGUEPEDIA_MIN_INTERVAL_SECONDS = 0.0
PANDASCORE_API_TOKEN = "test-token"
PANDASCORE_API_BASE = "https://api.pandascore.test"
LEAGUEPEDIA_API_BASE = "https://lol.leaguepedia.test"
LEAGUEPEDIA_BOT_USERNAME = "Tester@FantaLol"
LEAGUEPEDIA_BOT_PASSWORD = "bot-password"
MEDIA_ROOT = BASE_DIR / ".test-media"  # noqa: F405
