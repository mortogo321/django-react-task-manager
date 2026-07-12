#!/usr/bin/env sh
#
# Task Manager backend entrypoint.
#
# Runs at container start. Bootstraps anything the app needs before
# the main process takes over (gunicorn, runserver, pytest, …) and
# then `exec`s the original CMD so signals propagate cleanly.

set -eu

log() { printf '[start.sh] %s\n' "$*"; }


# ----------------------------------------------------------------------------
# 1. Generate a DJANGO_SECRET_KEY when one isn't provided.
#    Production must always supply its own (the dev fallback is gated
#    on DEBUG=True so a misconfigured prod container fails fast).
# ----------------------------------------------------------------------------
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    if [ "${DEBUG:-False}" = "True" ]; then
        DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
        export DJANGO_SECRET_KEY
        log "generated dev DJANGO_SECRET_KEY (DEBUG=True)"
    else
        log "ERROR: DJANGO_SECRET_KEY is required when DEBUG=False"
        exit 1
    fi
fi


# ----------------------------------------------------------------------------
# 2. Wait for Postgres. The compose healthcheck already gates the
#    backend on `service_healthy`, but this is a safety net for
#    deployments that don't.
# ----------------------------------------------------------------------------
if [ -n "${POSTGRES_HOST:-}" ]; then
    PORT="${POSTGRES_PORT:-5432}"
    log "waiting for ${POSTGRES_HOST}:${PORT}"
    i=0
    until python -c "
import socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('${POSTGRES_HOST}', ${PORT}))
except OSError:
    sys.exit(1)
" 2>/dev/null; do
        i=$((i + 1))
        if [ "$i" -ge 30 ]; then
            log "ERROR: ${POSTGRES_HOST}:${PORT} unreachable after 30s"
            exit 1
        fi
        sleep 1
    done
    log "database is reachable"
fi


# ----------------------------------------------------------------------------
# 3. Migrations. In dev we also auto-`makemigrations` so model edits
#    don't need a manual step. Production runs migrations as the
#    one-shot `migrate` service in docker-compose.prod.yml — set
#    SKIP_MIGRATE=1 there to skip this block.
# ----------------------------------------------------------------------------
if [ "${SKIP_MIGRATE:-0}" != "1" ]; then
    if [ "${DEBUG:-False}" = "True" ]; then
        log "makemigrations (dev)"
        python manage.py makemigrations workers tasks notifications --noinput || true
    fi
    log "migrate"
    python manage.py migrate --noinput
fi


# ----------------------------------------------------------------------------
# 4. Collect static (idempotent — no-op if already done at build time).
# ----------------------------------------------------------------------------
if [ "${SKIP_COLLECTSTATIC:-0}" != "1" ]; then
    python manage.py collectstatic --noinput >/dev/null 2>&1 || true
fi


# ----------------------------------------------------------------------------
# 5. Seed sample data.
#    `seed_data.py` is destructive — it wipes Tasks/Workers/Employers
#    and recreates a fixture. Hard guard: NEVER run when APP_ENV=prod.
#    For dev/uat, opt in via SEED_DATA=1 (default 0).
# ----------------------------------------------------------------------------
if [ "${APP_ENV:-dev}" != "prod" ] && [ "${SEED_DATA:-0}" = "1" ]; then
    log "seeding sample data (APP_ENV=${APP_ENV:-dev}, SEED_DATA=1)"
    python manage.py shell < seed_data.py || log "WARN: seed failed (continuing)"
elif [ "${SEED_DATA:-0}" = "1" ] && [ "${APP_ENV:-dev}" = "prod" ]; then
    log "ignoring SEED_DATA=1 — refusing to seed in prod"
fi


# ----------------------------------------------------------------------------
# 6. Hand off to the actual command (gunicorn, runserver, pytest, …).
# ----------------------------------------------------------------------------
log "exec $*"
exec "$@"
