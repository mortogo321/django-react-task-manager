# syntax=docker/dockerfile:1.7
#
# BaanTask backend — multi-stage build.
#
# Stages:
#   1. base    — pinned python base, common env, no extras
#   2. builder — installs build toolchain + python wheels into a venv
#   3. runtime — minimal image: copies the venv + app, drops privileges
#
# Why multi-stage:
#   - The builder pulls in gcc / libpq-dev / build-essential to compile
#     wheels (psycopg2, cryptography). None of that is needed at runtime.
#   - The runtime image only carries the venv and the libpq5 shared lib,
#     so the final image is ~50% smaller and the attack surface drops.
#   - Wheels are cached via BuildKit so iterative builds reuse them.

# ----------------------------------------------------------------------------
# 1. base — shared by builder and runtime
# ----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=60 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app


# ----------------------------------------------------------------------------
# 2. builder — compile and install dependencies into a relocatable venv
# ----------------------------------------------------------------------------
FROM base AS builder

# Build toolchain. These libs are *not* in the runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create the venv up-front so subsequent layers can install into it.
RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --upgrade pip setuptools wheel

# Copy only the requirements file first so the dependency layer is
# cached independently of source code changes.
COPY requirements.txt .

# BuildKit cache mount keeps wheels around between builds.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt


# ----------------------------------------------------------------------------
# 3. runtime — minimal image, no compilers, unprivileged user
# ----------------------------------------------------------------------------
FROM base AS runtime

# Runtime-only OS deps. libpq5 is the shared lib psycopg2 needs at
# runtime; curl is for the HEALTHCHECK; tini is PID 1.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app

# Bring the prebuilt venv across — fully self-contained, no pip step.
COPY --from=builder /opt/venv /opt/venv

# Pick the right env file for this image. Override at build time:
#     docker build --build-arg APP_ENV=prod ./backend
# Defaults to `dev` so a bare `docker build` produces a usable local
# image. Real secrets must still be injected at runtime via the
# orchestrator — the env file holds non-secret defaults.
ARG APP_ENV=dev
ENV APP_ENV=${APP_ENV}

# Copy the entrypoint script from the named `infra` build context.
# Compose wires this with `additional_contexts: infra: ./docker/backend`.
# Doing this *before* the application source so unrelated edits don't
# invalidate the script layer.
COPY --from=infra --chown=app:app start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy the application source last so source edits don't bust the
# dependency layer cache.
COPY --chown=app:app . /app

# Stamp the chosen env file as `.env` so python-dotenv picks it up at
# import time. We do this *after* the bulk COPY so the .env files
# themselves can change without invalidating earlier layers.
RUN cp /app/.env.${APP_ENV} /app/.env \
    && chown app:app /app/.env

# Compile static files at build time so the running container is
# read-only. `|| true` keeps this resilient if the project hasn't
# wired collectstatic yet.
RUN python manage.py collectstatic --noinput 2>/dev/null || true \
    && chown -R app:app /app

USER app
EXPOSE 8000

# tini reaps zombie children and forwards signals; start.sh runs the
# init bootstrap (gen secret key, wait for db, migrate, collectstatic)
# and then `exec`s the CMD so signals propagate cleanly to gunicorn.
ENTRYPOINT ["/usr/bin/tini", "--", "/app/start.sh"]

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/api/health/ || exit 1

# Production default. The dev compose file overrides this with
# `manage.py runserver` and bind-mounts /app for hot reload.
CMD ["gunicorn", "baantask.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "4", \
     "--timeout", "30", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]


# ----------------------------------------------------------------------------
# 4. dev — adds source-mount-friendly tooling on top of runtime
# ----------------------------------------------------------------------------
FROM runtime AS dev

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*
USER app

# No CMD override — docker-compose.yml's `command:` provides runserver.
