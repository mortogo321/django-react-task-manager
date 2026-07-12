# Task Manager — Day 1 Code Review

Issues are grouped by severity. Each entry lists the location, what's wrong, why it matters, and the fix that lands on Day 2.

---

## 🔴 Critical (security / correctness)

### 1. Header-based "auth" can be spoofed
**Where:** `backend/core/middleware.py`, `backend/core/permissions.py`
**Problem:** Identity comes from `X-Employer-Id` and `X-User-Role` HTTP headers — anyone with `curl` can claim to be any employer or escalate to `employer` role. Permissions only check `request.user_role` and never verify ownership.
**Why it matters:** Complete authentication bypass + privilege escalation.
**Fix:** Replace with real auth (DRF SessionAuth or SimpleJWT). Make `request.user` an actual `User` linked 1:1 to `Employer`. Keep the header path *only* under `if settings.DEBUG` for tests, and gate it with a fixed dev token. Add object-level `IsOwner` permission that checks `obj.employer_id == request.user.employer_id`.

### 2. Cross-tenant data leak — querysets are not scoped
**Where:** `backend/tasks/views.py:15`, `backend/workers/views.py:14`, `:70`
**Problem:** `queryset = Task.objects.all()` (and likewise for workers/employers). Any caller can list, retrieve, update, or delete *every* employer's records.
**Why it matters:** Multi-tenant data isolation is broken — the entire purpose of an employer model is undermined.
**Fix:** Override `get_queryset()` in each viewset to filter by `request.user.employer` (or, while debug auth is in place, by `request.current_employer`). Reject anonymous/unscoped requests with `403`.

### 3. IDOR on `/api/employers/{id}/dashboard/`
**Where:** `backend/workers/views.py:27` (`EmployerViewSet.dashboard`)
**Problem:** No ownership check. Any caller can `GET /api/employers/42/dashboard/` and read another employer's billing, full salary list, phone numbers, and worker roster.
**Why it matters:** PII + financial data leak. Classic IDOR.
**Fix:** Restrict the action so it only returns data when `pk == request.user.employer_id`, or simply expose it as `/api/me/dashboard/` and drop the path parameter.

### 4. Broken task state machine
**Where:** `backend/tasks/models.py:56` (`can_transition_to`)
**Problem:** The transition map is wrong:
```python
'created':     ['assigned'],
'assigned':    ['created'],         # only goes back, never forward
'in_progress': ['completed'],
'completed':   ['in_progress'],     # can be un-completed
'verified':    [],                  # dead-end with no incoming edge
```
There is no path `assigned → in_progress`, no path `completed → verified`, and `verified` is unreachable.
**Why it matters:** Frontend cannot move tasks through their lifecycle. The validator silently breaks the core workflow.
**Fix:**
```python
transitions = {
    'created':     ['assigned'],
    'assigned':    ['in_progress'],
    'in_progress': ['completed'],
    'completed':   ['verified'],
    'verified':    [],
}
```
Optionally allow backwards moves for admins via a separate `force=True` path.

### 5. `complete` action bypasses validation and skips `completed_at`
**Where:** `backend/tasks/views.py:21`
**Problem:**
```python
def complete(self, request, pk=None):
    task = self.get_object()
    task.status = 'completed'
    task.save()
```
Sets the status directly, ignoring `can_transition_to`, ignoring whether a worker is assigned, and never stamping `completed_at`.
**Why it matters:** State machine is unenforceable; reporting on `completed_at` is broken.
**Fix:** Validate the transition, set `completed_at = timezone.now()`, save inside `transaction.atomic()`, return the serialized task.

### 6. Worker-limit check has a TOCTOU race
**Where:** `backend/workers/serializers.py:36` (`WorkerSerializer.validate`)
**Problem:** Reads `count()` then lets the view `create()`. Two parallel requests can both pass the check and overshoot the plan limit.
**Why it matters:** Plans are revenue-bearing — this is a paid-feature bypass.
**Fix:** Move the check inside a `transaction.atomic()` block in `perform_create`/`perform_update`, with `Employer.objects.select_for_update().get(pk=...)` to lock the parent row for the duration.

### 7. Worker-limit check ignored on update / reactivation
**Where:** Same file. Checks only on create, only counts `is_active=True`, and never excludes `self.instance` on update.
**Problem:** Reactivating an inactive worker (or re-pointing a worker at another employer) can exceed the limit. PUT to update an existing worker re-runs validation but compares against `current_count >= limit` while the existing worker is itself counted, producing false positives on edits and false negatives on reactivation.
**Fix:** Centralize the check in a model method `Employer.assert_can_add_worker(exclude_pk=None)` and call it from both create and update paths, excluding the worker being edited.

---

## 🟠 High (perf / data quality)

### 8. N+1 queries on list endpoints
**Where:**
- `EmployerSerializer.get_worker_count` → 1 query per row
- `EmployerViewSet.dashboard` iterates `workers` and sums salary in Python
- `TaskSerializer.get_worker_name` → 1 query per row
**Fix:**
- `EmployerViewSet.get_queryset` → `annotate(worker_count=Count('workers'))`, drop the SerializerMethodField
- Dashboard → push the salary sum into the DB with `aggregate(Sum('salary'))`
- `TaskViewSet.get_queryset` → `select_related('employer', 'worker')`

### 9. Plan prices and limits are hardcoded in views
**Where:** `EmployerViewSet.dashboard` has the price table inline; `Employer.worker_limit` has the limit table on the model.
**Problem:** Two sources of truth, both hardcoded. Adding a plan means editing two places.
**Fix:** Move both into a single `PLANS` dict (or a `Plan` model) and read from it everywhere.

### 10. `Worker.salary` and `Employer.email` lack value-level validation
- `salary` accepts negative or zero values (`MinValueValidator(0)` missing).
- `start_date` accepts dates in the future.
- `due_date` on tasks accepts dates in the past.
**Fix:** Add `MinValueValidator`, custom clean methods, and serializer-level checks.

### 11. Free-text length is unbounded
- `Task.description` is `TextField` with no max — letting the API accept multi-megabyte payloads is a cheap DoS vector.
**Fix:** Soft limit in the serializer (e.g. 5_000 chars) and a global DRF `DATA_UPLOAD_MAX_MEMORY_SIZE`.

---

## 🟡 Medium (config / hygiene)

### 12. Insecure settings defaults shipped in code
**Where:** `backend/baantask/settings.py:14-18`
- `SECRET_KEY` falls back to a hardcoded "insecure" string.
- `DEBUG` defaults to `True`.
- `ALLOWED_HOSTS` defaults to localhost.
**Fix:** Require `DJANGO_SECRET_KEY` (raise if missing in production), default `DEBUG=False`, derive `ALLOWED_HOSTS` from env in prod.

### 13. CORS is hardcoded
**Where:** `settings.py:135`
**Fix:** Read `CORS_ALLOWED_ORIGINS` from env so prod doesn't need a code change.

### 14. No CSRF strategy for the SPA
The SPA uses cookies-less axios but Django's CSRF middleware is enabled. Once real auth lands, every POST/PUT/DELETE will 403 unless CSRF tokens are wired or session-cookie auth is replaced with token auth.
**Fix:** Decide on JWT (drop CSRF for `/api/*`) or session + `csrftoken` cookie wiring.

### 15. No tests, no OpenAPI docs, no logging
- Zero test files.
- No `drf-spectacular` / `drf-yasg`.
- `print()` in `seed_data.py`, no structured logging anywhere.
**Fix (Day 2):** Add `pytest-django`, `drf-spectacular`, a `LOGGING` config.

### 16. Worker `Meta.ordering = ['first_name']` is locale-naive
Sorting Thai names alphabetically by Latin transliteration produces nonsense ordering for the actual native data.
**Fix:** Order by `created_at` or expose `ordering` as a query parameter only.

---

## 🟢 Frontend issues

### 17. Pagination is silently truncated
**Where:** `frontend/src/components/TaskList.js:37`, `WorkerList.js:30`
```js
setTasks(response.data.results || response.data);
```
Reads `results` but ignores `count`/`next`/`previous`. Past page 1, the user sees a 20-item slice with no UI affordance to paginate.
**Fix:** Add a pagination component or switch the API default to a much higher page size for now.

### 18. `useEffect` deps miss `fetchTasks`
**Where:** `TaskList.js:26`
```js
useEffect(() => { fetchTasks(); fetchStats(); }, [statusFilter]);
```
Works today because both functions are stable closures, but lints/strict mode will complain and any future dependency change creates a stale closure.
**Fix:** Wrap in `useCallback` or inline the fetch inside the effect.

### 19. Errors surfaced via `alert()`
**Where:** `TaskList.js:61`
**Fix:** Inline error banner with retry, plus a global axios error toast.

### 20. No mobile/responsive layout, no a11y
- Inline styles, hard-coded widths, no media queries.
- No focus states, no `aria-*` on the tab buttons, no contrast review.
**Fix (Day 3):** Move to CSS modules or Tailwind, add a mobile layout, basic a11y pass.

### 21. No "create task" / "create worker" UI
The whole CRUD surface exists on the backend but only `complete` is wired. Users can't add data without `seed_data.py`. **Fix (Day 3):** Forms with validation and optimistic updates.

### 22. `complete` button only shows for `in_progress`
And `can_transition_to` (Day 2 fix) means only `in_progress → completed` is legal. Today the user can't even reach `in_progress` from the UI. **Fix (Day 3):** Add a status dropdown that respects the state machine.

### 23. Hardcoded health-status assumption
**Where:** `App.js:28` — checks `health?.status === 'healthy'`. The backend always returns `healthy` even when the DB check fails (it embeds the error in `database` instead of changing `status`).
**Fix:** Backend should return `degraded`/`unhealthy` when the DB check fails; frontend should reflect that.

---

## Approach for Day 2

1. Bring up `User`-backed auth (start with DRF Token + a `dev_login` endpoint).
2. Scope every viewset queryset to `request.user.employer`.
3. Add `IsOwner` object-permission and apply to the dashboard action.
4. Fix `can_transition_to` and the `complete` action; add `completed_at`.
5. Move worker-limit check into `perform_create`/`perform_update` with `select_for_update`.
6. Annotate / `select_related` to kill N+1.
7. Tighten settings (env-only secret, debug, hosts, CORS).
8. Add `drf-spectacular` for OpenAPI at `/api/schema/` + Swagger UI at `/api/docs/`.
9. Write pytest cases for: cross-tenant scoping, IDOR on dashboard, transitions, worker-limit race, dashboard aggregation.
10. Short report on AI-tool usage.
