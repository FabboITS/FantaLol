# syntax=docker/dockerfile:1
# Contesto di build: la root del repository (serve anche la cartella frontend/).

# --- build: dipendenze in un virtualenv isolato ----------------------------------------------------
FROM python:3.12-slim AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY backend/pyproject.toml ./
RUN python -m venv /venv && /venv/bin/pip install --upgrade pip && /venv/bin/pip install .

# --- runtime ---------------------------------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod FRONTEND_DIR=/app/frontend MEDIA_ROOT=/app/media PORT=8080
RUN useradd --create-home --uid 1000 fantalol
COPY --from=build /venv /venv
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
WORKDIR /app/backend
RUN mkdir -p /app/media && chown -R fantalol:fantalol /app/media
USER fantalol
EXPOSE 8080
# Il servizio "web" esegue migrate + ensure_admin all'avvio; "scheduler" sovrascrive il comando.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py ensure_admin && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS:-3} --timeout 60 --access-logfile -"]
