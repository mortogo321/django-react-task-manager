"""
Claude API wrapper for Task Manager translations.

Design goals:
- Pure function interface (`translate(text, target, source=None) -> str`)
  so callers don't depend on Anthropic types.
- Two-tier caching: in-process LRU (per-worker) + Redis (cluster-wide).
- Stable cache keys: SHA-256 of `(model, source, target, normalized_text)`.
- Resilience: timeout, single retry on 5xx / `RateLimitError`,
  graceful fallback (returns the original text and logs).
- Cheap to call: a 1-character hash lookup before any network I/O.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger("baantask.translation")


# ---- public API ------------------------------------------------------------


@dataclass(frozen=True)
class TranslationResult:
    text: str
    cached: bool
    fallback: bool  # True when the original text was returned unchanged


# Hard cap on a single translation request to keep cost and prompt size
# bounded. The serializer enforces a 5_000-char limit on
# `Task.description`; this is the lower-level safety net.
MAX_INPUT_CHARS = 8_000


def translate(
    text: str,
    target: str,
    source: Optional[str] = None,
    *,
    model: Optional[str] = None,
) -> TranslationResult:
    """
    Translate `text` to language code `target` (e.g. 'th', 'en').
    Returns the original text wrapped in TranslationResult on any failure.
    """
    text = (text or "").strip()
    if not text:
        return TranslationResult(text="", cached=True, fallback=False)
    if len(text) > MAX_INPUT_CHARS:
        log.warning(
            "translation input too long (%d chars > %d); falling back",
            len(text),
            MAX_INPUT_CHARS,
        )
        return TranslationResult(text=text, cached=False, fallback=True)
    if source and source == target:
        return TranslationResult(text=text, cached=True, fallback=False)

    model = model or settings.TRANSLATION_MODEL
    key = _cache_key(model, source or "auto", target, text)

    cached = cache.get(key)
    if cached is not None:
        return TranslationResult(text=cached, cached=True, fallback=False)

    try:
        translated = _call_claude(text=text, target=target, source=source, model=model)
    except Exception as exc:  # network / API failure → fallback
        log.warning("translation failed (%s); falling back to original", exc)
        return TranslationResult(text=text, cached=False, fallback=True)

    cache.set(key, translated, timeout=settings.TRANSLATION_CACHE_TTL)
    return TranslationResult(text=translated, cached=False, fallback=False)


# ---- internals -------------------------------------------------------------


def _cache_key(model: str, source: str, target: str, text: str) -> str:
    digest = hashlib.sha256(
        f"{model}|{source}|{target}|{text}".encode("utf-8")
    ).hexdigest()
    # `tr:` namespace + first 32 chars is enough entropy and short enough
    # for Redis hot keys.
    return f"tr:{target}:{digest[:32]}"


@functools.lru_cache(maxsize=1)
def _client():
    """
    Lazy-construct the Anthropic client. We import inside the function so
    importing this module never fails when the package isn't installed
    (e.g. during settings tests).
    """
    from anthropic import Anthropic  # type: ignore[import-not-found]

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.TRANSLATION_TIMEOUT,
    )


_LANGUAGE_NAMES = {
    "en": "English",
    "ru": "Russian",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "th": "Thai",
}


def _call_claude(
    *, text: str, target: str, source: Optional[str], model: str
) -> str:
    target_name = _LANGUAGE_NAMES.get(target, target)
    source_name = _LANGUAGE_NAMES.get(source or "", "the source language")
    system = (
        "You are a professional translator for a household-staff "
        "management app used in Thailand. Translate the user's message "
        f"from {source_name} to {target_name}. Preserve names, numbers, "
        "and times exactly. Return only the translation — no commentary, "
        "no quotes, no preamble."
    )

    last_exc: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            resp = _client().messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": text}],
            )
            return _extract_text(resp).strip()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            cls = exc.__class__.__name__
            retriable = cls in {
                "RateLimitError",
                "APIConnectionError",
                "APITimeoutError",
                "InternalServerError",
            }
            if attempt == 2 or not retriable:
                break
            time.sleep(0.4 * attempt)
    assert last_exc is not None
    raise last_exc


def _extract_text(response) -> str:
    """
    Anthropic responses return a list of content blocks; we only care
    about text blocks here.
    """
    blocks = getattr(response, "content", []) or []
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts) if parts else str(response)
