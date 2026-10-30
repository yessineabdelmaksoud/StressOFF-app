"""Shared fixtures for the backend service tests.

The services read OPENROUTER_API_KEY at import time, so a dummy value is set
here before any service module is imported. Every OpenRouter call is replaced
by a fake response; real HTTP requests are blocked so the tests never need
network access or real keys.
"""

import json
import os

import pytest
import requests

os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code=200, payload=None, text="", lines=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")
        self._lines = lines or []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"{self.status_code} error")

    def iter_lines(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def chat_completion(content):
    """Build an OpenRouter chat completion payload whose message is `content`."""
    if not isinstance(content, str):
        content = json.dumps(content)
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail loudly if a test forgets to mock an outgoing HTTP call."""

    def _blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in tests")

    monkeypatch.setattr(requests.sessions.Session, "request", _blocked)


@pytest.fixture
def fake_openrouter(monkeypatch):
    """Replace requests.post with a fake that records calls.

    Usage: ``calls = fake_openrouter(FakeResponse(...))``; each call made by the
    service is appended to ``calls`` as ``(url, kwargs)``.
    """

    def _install(response):
        calls = []

        def _post(url, **kwargs):
            calls.append((url, kwargs))
            return response

        monkeypatch.setattr(requests, "post", _post)
        return calls

    return _install
