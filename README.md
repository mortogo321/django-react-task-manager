# BaanTask

AI-powered household staff management platform for expats in Thailand.
Employers can create tasks for their staff (maids, nannies, drivers,
cooks), auto-translate them to Thai via Claude, and track them through
a state machine.

## Stack

- **Backend** — Django 5 + DRF, drf-spectacular, anthropic, Ruff
- **Frontend** — React 18 (CRA), Bun, Biome
- **Database** — PostgreSQL 16
- **Cache** — Redis 7
- **Runtime** — Multi-stage Docker, gunicorn (tini), nginx
- **CI/CD** — GitHub Actions: `quality → test → build → deploy`

## Quick start (dev)

```bash
docker compose up --build
```

| Service              | URL                                  |
|----------------------|--------------------------------------|
| Frontend             | http://localhost:3000                |
| API                  | http://localhost:8000/api/           |
| API docs (Swagger)   | http://localhost:8000/api/docs/      |
| API docs (Redoc)     | http://localhost:8000/api/redoc/     |
| OpenAPI schema       | http://localhost:8000/api/schema/    |
| Health               | http://localhost:8000/api/health/    |

The dev environment auto-seeds sample data on first boot
(`backend/.env.dev` sets `SEED_DATA=1`; `docker/backend/start.sh`
hard-refuses to seed when `APP_ENV=prod`).

## Auth (dev only)

The frontend stores the active employer id in `localStorage` and sends
it on every request via `X-Employer-Id`. The header dropdown lets you
switch employers. The backend `SimpleAuthMiddleware` reads the header
and resolves it to an `Employer`. **This is dev-only — production must
replace it with JWT/session auth.** See `docs/CODE_REVIEW.md` for the
threat model.

## Project layout

```
backend/
  baantask/         Django project (settings, urls, wsgi)
  core/             Auth middleware, permissions, throttling, request-id, health
  workers/          Employer + Worker domain
  tasks/            Task domain (state machine)
  translation/      Claude wrapper + Redis cache
  notifications/    Event log + per-employer prefs
  conftest.py       Pytest fixtures (employer/api/task/worker)
  pyproject.toml    Ruff + pytest config
  Dockerfile        Multi-stage: base → builder → runtime → dev
  .dockerignore
  .env.dev .env.uat .env.prod
  manage.py  seed_data.py  requirements.txt

frontend/
  src/
    api/            Axios client (auth header, error normalization, pagination)
    components/     TaskList, TaskForm, WorkerList, Dashboard, NotificationsBell, Modal
    App.js  index.js  styles.css
  Dockerfile        Multi-stage: deps → dev → build → runtime (nginx)
  .dockerignore
  biome.json        Lint + format + import-sort
  package.json      Bun-driven scripts: start / build / check / ci:check
  .env.dev .env.uat .env.prod

docker/             Build-time auxiliary files (consumed via additional_contexts)
  backend/start.sh    init: gen secret → wait db → migrate → collectstatic → seed → exec
  frontend/start.sh   pass-through entrypoint (placeholders for future init)
  nginx/nginx.conf    SPA + /api proxy, listens on :8080 for non-root nginx

docs/               Task-required documentation (see "Docs" below)

docker-compose.yml          dev (target: dev, source bind-mounts, hot reload)
docker-compose.uat.yml      UAT overlay (target: runtime, APP_ENV=uat, :uat tag)
docker-compose.prod.yml     Prod overlay (target: runtime, APP_ENV=prod, :latest tag)

.github/workflows/deploy.yml   CI: quality → test → build → deploy
CANDIDATE_TASKS.md             Original test brief
```

## Multi-stage Docker

Both Dockerfiles are multi-stage with named stages so each compose
file picks the right one via `target:`.

**Backend** (`backend/Dockerfile`):
- `base` — pinned `python:3.12-slim-bookworm`, common env vars
- `builder` — installs build toolchain (`gcc`, `libpq-dev`) and Python
  wheels into a relocatable venv with a BuildKit pip cache mount
- `runtime` — minimal image: copies the venv + app, installs only
  `libpq5`/`curl`/`tini`, drops to unprivileged `app:1001`, gunicorn
  with sane defaults (3 × 4 × 30s, max-requests 1000+jitter), tini as
  PID 1, healthcheck against `/api/health/`
- `dev` — `runtime` + `postgresql-client` for `manage.py dbshell`

**Frontend** (`frontend/Dockerfile`):
- `deps` — `oven/bun:1.1-alpine` + `bun install` with cache mount
- `dev` — copies source, runs `bun run start` for the CRA dev server
- `build` — `bun run build`, no source maps, hashed bundle
- `runtime` — `nginx:1.27-alpine`, serves the built bundle from
  `/usr/share/nginx/html`, listens on :8080 as the `nginx` user

Auxiliary files under `docker/` are exposed to each build via Compose
`additional_contexts`:

```yaml
backend:
  build:
    context: ./backend
    additional_contexts:
      infra: ./docker/backend       # → COPY --from=infra start.sh
frontend:
  build:
    context: ./frontend
    additional_contexts:
      infra: ./docker/frontend      # → COPY --from=infra start.sh
      nginx: ./docker/nginx         # → COPY --from=nginx nginx.conf
```

## Environments

Three per-environment files live next to each Dockerfile and are baked
into the image at build time via the `APP_ENV` build arg
(`COPY .env.${APP_ENV} .env`):

| Env  | Backend file              | Frontend file              |
|------|---------------------------|----------------------------|
| dev  | `backend/.env.dev`        | `frontend/.env.dev`        |
| uat  | `backend/.env.uat`        | `frontend/.env.uat`        |
| prod | `backend/.env.prod`       | `frontend/.env.prod`       |

These files contain **non-secret defaults** only. Real secrets
(`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `ANTHROPIC_API_KEY`) are
injected at deploy time from CI variables — the prod and UAT compose
files use `${VAR:?...}` placeholders that fail-fast when a required
value is missing. python-dotenv does **not** override existing env
vars, so the runtime environment always wins over the baked-in
defaults.

### Bring up each environment

```bash
# Dev
docker compose up --build

# UAT
docker compose -f docker-compose.yml -f docker-compose.uat.yml up --build -d

# Prod
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Container init (`docker/backend/start.sh`)

The backend image's ENTRYPOINT runs `start.sh`, which bootstraps
everything Django needs before handing off to gunicorn / runserver:

1. **Generate `DJANGO_SECRET_KEY`** if missing — only when `DEBUG=True`
   (a misconfigured prod container fails fast).
2. **Wait for Postgres** (up to 30 s) before continuing.
3. **Migrate** — auto-`makemigrations` in dev, plain `migrate` everywhere
   (skip via `SKIP_MIGRATE=1`; the prod overlay also runs a one-shot
   `migrate` service).
4. **`collectstatic`** (skip via `SKIP_COLLECTSTATIC=1`).
5. **Seed sample data** if `SEED_DATA=1` — hard-refuses when
   `APP_ENV=prod`.
6. **`exec "$@"`** so signals reach gunicorn cleanly under tini.

The frontend image's ENTRYPOINT is `docker/frontend/start.sh`, which
is a pass-through today (placeholders for future runtime config
injection / vhost templating).

## Tests

```bash
docker compose exec backend pytest -q
```

20+ pytest cases covering: state machine, transitions API, PATCH state
machine, cross-tenant scoping, worker-limit race, dashboard IDOR,
dashboard aggregation, anon block, unknown-employer block, translation
cache hit, translation fallback.

## Code quality

```bash
# Backend (Ruff)
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .

# Frontend (Biome — lint + format + import-sort in one pass)
docker compose exec frontend bun run check       # report
docker compose exec frontend bun run check:fix   # auto-fix
docker compose exec frontend bun run ci:check    # CI mode (no fixes)
```

Configs: `backend/pyproject.toml` (Ruff rules + isort + format), `frontend/biome.json`.
CI runs `ruff check`, `ruff format --check`, and `biome ci .` in the
quality stage before tests.

## CI / CD

GitHub Actions pipeline (`.github/workflows/deploy.yml`):

```
quality-backend ──┐
                  ├──► test ──► build ──► deploy
quality-frontend ─┘
```

- **quality** — Ruff (backend) + Biome (frontend) in parallel.
- **test** — pytest with Postgres + Redis service containers.
- **build** — multi-stage Docker images, pushed to ghcr with `:sha`
  and `:latest` tags. `APP_ENV=prod` baked in via build arg.
  Pull-through GHA cache scoped per image.
- **deploy** — `docker compose up -d` against the production host with
  secrets and vars sourced from the GitHub environment.

PR builds run quality + test only. Push to `main` runs the full
pipeline. `concurrency` cancels superseded runs on the same branch.

### Required CI configuration

| GitHub setting               | Name                  | Notes                                       |
|------------------------------|-----------------------|---------------------------------------------|
| Secrets → Actions            | `DJANGO_SECRET_KEY`   | 50+ random chars                            |
| Secrets → Actions            | `POSTGRES_PASSWORD`   | DB password                                 |
| Secrets → Actions            | `ANTHROPIC_API_KEY`   | Claude API key                              |
| Secrets → Actions            | `REGISTRY_USERNAME`   | ghcr login                                  |
| Secrets → Actions            | `REGISTRY_PASSWORD`   | ghcr token                                  |
| Variables → Actions          | `ALLOWED_HOSTS`       | e.g. `api.baantask.app`                     |
| Variables → Actions          | `CORS_ALLOWED_ORIGINS`| e.g. `https://app.baantask.app`             |
| Variables → Actions          | `BACKEND_IMAGE`       | e.g. `ghcr.io/acme/baantask-backend`        |
| Variables → Actions          | `FRONTEND_IMAGE`      | e.g. `ghcr.io/acme/baantask-frontend`       |
| Variables → Actions          | `REACT_APP_API_URL`   | e.g. `https://api.baantask.app/api`         |

## Docs

Task-required deliverables (see `CANDIDATE_TASKS.md`):

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Day 1: architecture, modules, data model.
- [`docs/CODE_REVIEW.md`](docs/CODE_REVIEW.md) — Day 1: code-review findings (severity, location, fix).
- [`docs/AI_USAGE.md`](docs/AI_USAGE.md) — Day 2: short report on AI tool usage.
- [`docs/TRANSLATION_SCALING.md`](docs/TRANSLATION_SCALING.md) — Day 4: translation service architecture and 10k req/min plan.

API documentation is auto-generated by drf-spectacular and served at
`/api/docs/` (Swagger UI), `/api/redoc/` (Redoc), `/api/schema/`
(OpenAPI JSON).
