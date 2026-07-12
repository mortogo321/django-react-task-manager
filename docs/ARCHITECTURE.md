# Task Manager — Architecture Overview

## High-level

Task Manager is a thin three-tier app:

```
React SPA  ──HTTP──►  Django + DRF  ──►  PostgreSQL
                            │
                            └──►  Redis (cache)
```

Everything runs in `docker compose`:

| Service   | Image / Build       | Port  | Role                                  |
|-----------|---------------------|-------|---------------------------------------|
| `db`      | `postgres:16-alpine`| 5432  | Primary datastore                     |
| `redis`   | `redis:7-alpine`    | 6379  | Cache backend (Django cache + future translation cache) |
| `backend` | `./backend`         | 8000  | Django 5 + DRF API                    |
| `frontend`| `./frontend`        | 3000  | React 18 dev server (CRA)             |

## Backend layout (`backend/`)

```
baantask/         ← Django project (settings, urls, wsgi)
core/             ← Cross-cutting: auth middleware, permissions, health
workers/          ← Employer + Worker domain
tasks/            ← Task domain
manage.py
seed_data.py      ← Dev-only fixture loader
```

### Apps

- **`core`** — `SimpleAuthMiddleware` reads `X-Employer-Id` and `X-User-Role` headers and pins them on the request. `RoleBasedPermission` is the global DRF permission and only blocks workers from non-safe methods. `HealthCheckView` returns DB status.
- **`workers`** — `Employer` and `Worker` models, ModelViewSets with filter/search, plus two custom actions on `EmployerViewSet` (`workers/`, `dashboard/`).
- **`tasks`** — `Task` model + ModelViewSet with `complete/` and `stats/` actions.

### URL surface (`baantask/urls.py`)

```
/admin/
/api/health/
/api/workers/         (CRUD)
/api/employers/       (CRUD + /workers/ + /dashboard/)
/api/tasks/           (CRUD + /complete/ + /stats/)
```

DRF defaults: `PageNumberPagination` (page size 20), `DjangoFilterBackend`, `SearchFilter`, `OrderingFilter`. CORS is open to `localhost:3000` only.

## Data model

```
Employer ───1:N──► Worker
   │                 │
   │                 │
   └──1:N──► Task ◄──┘   (Worker is optional on Task)
```

### `Employer`
- `first_name`, `last_name`, `email` (unique), `phone`
- `preferred_language` (choices: en/ru/zh/ja/ko/fr/de/th) — used for upcoming translation feature
- `plan` (free/home/management/corporate) — drives `worker_limit` (1/3/10/999)
- Timestamps

### `Worker`
- Personal: `first_name`, `last_name`, `nickname` (Thai), `phone`
- `role` (maid/nanny/driver/cook/gardener/guard/other)
- `employer` → FK CASCADE
- `salary` (THB), `start_date`, `is_active`, `notes`
- Timestamps

### `Task`
- `title`, `description`
- `employer` → FK CASCADE (always set)
- `worker` → FK SET_NULL (optional / unassigned tasks allowed)
- `status` (created → assigned → in_progress → completed → verified)
- `priority` (low/medium/high/urgent)
- `due_date`, `completed_at`, timestamps
- `can_transition_to(new_status)` — declares legal transitions

### Relationships at a glance
- Deleting an Employer cascades to their Workers and Tasks.
- Deleting a Worker nulls the `worker` FK on Tasks (history is preserved).
- A Task always belongs to exactly one Employer; Worker assignment is mutable.

## Frontend layout (`frontend/`)

```
src/
  index.js
  App.js                 ← header, tab switcher, health badge
  api/client.js          ← axios instance + endpoint maps (workers/employers/tasks/health)
  components/
    TaskList.js          ← list, status filter, stats bar, "complete" button
    WorkerList.js        ← grid of cards, role filter
```

- React 18 (CRA), `axios`, no state library, no router (single-page tab toggle).
- API base from `REACT_APP_API_URL` (`http://localhost:8000/api` in dev).
- Inline-style objects per component (no design system, no CSS modules).

## Request lifecycle (current state)

1. SPA calls e.g. `GET /api/tasks/` via axios.
2. CORS middleware → `SimpleAuthMiddleware` reads headers → DRF view runs.
3. `RoleBasedPermission` checks role; viewset returns serialized data.
4. Frontend renders cards.

## Notable gaps (covered in `CODE_REVIEW.md`)

- "Auth" is a trust-the-client header — no real identity.
- Querysets are not scoped per employer → cross-tenant data leak.
- Task state machine in `can_transition_to` is broken.
- N+1 in serializers and dashboard.
- `EmployerViewSet.dashboard` is an IDOR.
- Worker-limit check has a TOCTOU race and ignores updates.
- No tests, no API docs, no real translation feature yet.

These are addressed in Day 2 onward.
