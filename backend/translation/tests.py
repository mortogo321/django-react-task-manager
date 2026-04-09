"""Translation service tests — uses a fake Claude client."""

from unittest.mock import patch

import pytest
from django.core.cache import cache

from translation import service


class _FakeTextBlock:
    def __init__(self, text: str):
        self.text = text


class _FakeResponse:
    def __init__(self, text: str):
        self.content = [_FakeTextBlock(text)]


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = 0
        self.messages = self

    def create(self, *, model, max_tokens, system, messages):
        self.calls += 1
        # Echo a fake "translation" so we can assert behavior.
        return _FakeResponse(f"[TH] {messages[0]['content']}")


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def fake_client(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(service, "_client", lambda: fake)
    return fake


def test_empty_text_returns_empty(fake_client):
    result = service.translate("", target="th")
    assert result.text == ""
    assert fake_client.calls == 0


def test_same_source_target_skips_api(fake_client):
    result = service.translate("hello", target="en", source="en")
    assert result.text == "hello"
    assert fake_client.calls == 0


def test_translation_caches_result(fake_client):
    a = service.translate("Clean kitchen", target="th", source="en")
    assert a.text == "[TH] Clean kitchen"
    assert a.cached is False
    assert fake_client.calls == 1

    b = service.translate("Clean kitchen", target="th", source="en")
    assert b.text == "[TH] Clean kitchen"
    assert b.cached is True
    assert fake_client.calls == 1  # not called again


def test_failure_falls_back_to_original(monkeypatch):
    class _BoomClient:
        messages = None

        def create(self, **kwargs):
            raise RuntimeError("boom")

    boom = _BoomClient()
    boom.messages = boom
    monkeypatch.setattr(service, "_client", lambda: boom)

    result = service.translate("Pick up kids", target="th", source="en")
    assert result.fallback is True
    assert result.text == "Pick up kids"
