from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
DATABASES["default"].update(  # noqa: F405
    __import__("dj_database_url").parse(
        env("DATABASE_URL", "postgres://fantalol:fantalol@localhost:5433/fantalol") or ""
    )
)
WHITENOISE_AUTOREFRESH = True
