# AI Usage Report

I used Claude Code as a pair-programmer throughout the assignment.
**Where it helped most:** scaffolding the boring stuff fast — DRF
viewsets, serializer skeletons, pytest fixtures, docker-compose tweaks,
and the OpenAPI annotations. I gave Claude the failing tests as context
and it filled in the boilerplate that would have eaten an hour of typing.

**Where I had to drive manually:** the security review and the
state-machine fix were judgment calls that needed me to read the
existing code and understand intent before deciding how to break or
keep behavior. The auth model in particular — I deliberately *kept* the
header-based middleware (with stricter validation) instead of replacing
it with JWT, because the test brief clearly treats real auth as out of
scope. I also rewrote the worker-limit check by hand: the obvious
"add `select_for_update`" suggestion still missed the update/reactivation
case, and I needed to centralize it on the model. The translation
service's two-tier cache key, retry policy, and fallback semantics were
likewise human-designed; Claude helped me articulate them in code.

**Net:** AI made me ~2× faster on typing, ~1× on thinking.
