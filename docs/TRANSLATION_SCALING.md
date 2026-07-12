# Scaling the Task Manager Translation Service to 10,000 req/min

10,000 req/min ≈ **167 req/s sustained**, with realistic peaks of
3–4× during evening household-task hours in Bangkok. The hard
constraints are:

1. Anthropic API rate limits and per-request latency (~600 ms p50,
   2–4 s p95 for short messages).
2. Cost — every uncached call is paid tokens.
3. Tail latency must stay under ~1 s p95 for the user-facing path
   (creating a task in the SPA).

## Current state (single-process, inline)

Today the `translation/service.py` wrapper is called inline from
`TaskViewSet._after_create`. It already does:

- **Two-tier cache**: process-local (LRU) is intentionally absent today —
  Django's Redis cache is the only layer — but the `translate()` call
  hashes a stable cache key from `(model, source, target, normalized_text)`
  and stores results for 7 days.
- **Bounded timeouts** (`TRANSLATION_TIMEOUT`, default 10 s).
- **Single retry** on retriable errors (`RateLimitError`, `APIConnectionError`,
  `APITimeoutError`, `InternalServerError`).
- **Graceful fallback**: returns the source text and logs on hard failure.

That's enough for ~5–10 req/s. Beyond that, three problems show up:

1. The Django request thread blocks on Anthropic for hundreds of ms.
2. Redis is the only cache, so every miss is a network round trip.
3. Bursts can exhaust Anthropic's per-org RPM budget.

## Target architecture

```
                   ┌─────────────────────────────────────┐
                   │            Django API               │
   POST /tasks ───►│  TaskViewSet._after_create          │
                   │     │                               │
                   │     └─►  enqueue(translate_task)    │
                   └────────────────┬────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │    Redis Streams /    │
                        │  Celery broker (RMQ)  │
                        └──────────┬────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
        ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
        │ translation  │   │ translation  │   │ translation  │
        │  worker #1   │   │  worker #2   │   │  worker #N   │
        └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
               │                  │                  │
               └─────────► L1 in-process LRU         │
                             │                       │
                             ▼                       ▼
                          Redis Cluster ◄────────────┘
                             │
                             ▼
                    Anthropic API (with token bucket
                       + circuit breaker + retries)
```

### Layer-by-layer

#### 1. Decouple translation from the request path
- Move the `_after_create` hook from inline to a queue (Celery, RQ, or
  Django-Q on Redis Streams).
- Persist `translation_status` on `Task` (`pending` → `done` / `failed`).
- The SPA renders the source text immediately and reveals
  `description_th` as soon as the websocket / poll says it's ready.
- This alone removes Anthropic latency from the user-visible path.

#### 2. Two-tier cache (L1 + L2)
- **L1 — in-process LRU** keyed by the same SHA-256 hash, ~50k entries
  per worker, ~30 min TTL. Cost: a few MB of RAM, zero network. Catches
  the "same task created twice in a minute" pattern that dominates real
  workloads.
- **L2 — Redis Cluster** with the existing 7-day TTL. Sharded across
  enough nodes to keep per-shard memory bounded. Use a hash-tagged key
  (`tr:{th}:{hash}`) so all variants of one phrase land on the same shard
  for atomic ops.
- **Cache hit rate target:** ≥85% for steady-state production. Household
  tasks repeat heavily ("clean kitchen", "pick up kids", "buy milk").
- Negative caching for empty / fallback responses with a short TTL
  (60 s) so a transient failure doesn't hammer Anthropic.

#### 3. Worker pool
- N async Python workers (asyncio + `anthropic.AsyncAnthropic`) pulling
  from the queue. Each handles ~50–100 in-flight requests.
- Per-worker concurrency cap so a slow upstream doesn't blow up memory.
- Horizontal autoscaling on queue depth (e.g. KEDA → HPA on Kubernetes).
- 4–8 workers each running 100 concurrent calls is enough for 167 req/s
  sustained, with headroom for bursts.

#### 4. Anthropic-side rate management
- **Token bucket** in front of the API client, sized to org RPM budget
  *minus* a safety margin. Refill rate ~80% of the published RPM.
- **Concurrency semaphore** per model to keep us under the per-minute
  *and* per-minute *output token* budget.
- **Circuit breaker**: open after 5 consecutive 5xx/timeouts in 30 s,
  half-open after 60 s. While open, all calls fall back to the source
  text and increment a `translation_circuit_open` metric.
- **Smart retries**: exponential backoff with jitter on 429 / 5xx, never
  retry on 4xx other than 429. Cap total per-request latency budget at
  3 s so the queue doesn't back up under partial failures.

#### 5. Cost controls
- **Model routing**: use Haiku for short, low-stakes content (titles,
  descriptions), reserve Sonnet for long messages (>1k chars). The
  cache key includes `model`, so a re-translation with a bigger model
  is a different entry.
- **Prompt caching** (Anthropic prompt-cache feature): cache the long
  system instructions once, reuse across requests — typical 70–90%
  prompt-token discount.
- **Batching**: when the queue holds N pending translations for the
  same target language, send them in a single multi-message request
  where possible, saving per-call overhead.

#### 6. Observability
- Metrics: req/s, cache-hit-ratio (L1, L2, total), p50/p95/p99
  latency, Anthropic 4xx/5xx rate, retry rate, circuit-breaker state,
  fallback count, $/hour estimate from token usage.
- Tracing: each `translate()` call gets a span with `cached`, `model`,
  `target`, `source`, and token counts.
- Alerts: cache-hit ratio < 70% over 10 min, fallback rate > 1%,
  circuit breaker open, queue lag > 30 s.

## Capacity math

- Sustained: 167 req/s.
- Assume 85% cache hit ratio → **25 req/s** to Anthropic.
- 25 req/s × 800 ms p50 = ~20 in-flight calls. Trivially handled by a
  single worker process; we run 4 for redundancy and to soak up bursts.
- Peak (4× burst): 100 in-flight Anthropic calls. Still within typical
  org limits. The token bucket smooths this out.

## Failure modes and mitigations

| Failure                                  | Mitigation                                       |
|------------------------------------------|--------------------------------------------------|
| Anthropic outage / region-wide 5xx       | Circuit breaker opens; tasks ship in source lang; bell shows "translations delayed" |
| Redis outage                             | L1 LRU absorbs hot keys; queue keeps state on disk via the broker |
| Worker pool overwhelmed                  | Queue depth alarm → autoscale; backpressure exposed via 429 from the SPA-facing endpoint |
| Cost overrun (a runaway loop creates 1M tasks) | Per-employer rate limit + daily token budget circuit breaker |
| Bad / abusive content                    | Pre-filter on the inbound side (Day 6 work — content moderation classifier) |

## What stays the same

The public API (`translate(text, target, source)`) does not change. The
upgrade path is all infrastructural — wrap the existing wrapper, move it
behind a queue, add the L1 cache and the breaker. None of the calling
code in `tasks/views.py` or `notifications/events.py` needs to know.
