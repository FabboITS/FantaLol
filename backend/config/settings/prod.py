from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import SIMPLE_JWT, env

DEBUG = False

if not env("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY è obbligatoria in produzione")
_jwt_secret = env("JWT_SECRET")
if not _jwt_secret or len(_jwt_secret) < 32:
    raise ImproperlyConfigured("JWT_SECRET è obbligatoria in produzione e deve contenere almeno 32 caratteri")
SIMPLE_JWT["SIGNING_KEY"] = _jwt_secret

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
