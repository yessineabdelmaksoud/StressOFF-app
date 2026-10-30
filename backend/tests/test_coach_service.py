import json

from fastapi.testclient import TestClient

from backend.coach_service import main as coach_main
from backend.tests.conftest import FakeResponse

client = TestClient(coach_main.app)


def _sse_events(text):
    return [line[len("data: "):] for line in text.splitlines() if line.startswith("data: ")]


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["endpoints"] == ["/coach"]


def test_coach_streams_content_chunks_then_done(fake_openrouter):
    calls = fake_openrouter(
        FakeResponse(
            lines=[
                b": OPENROUTER PROCESSING",
                b'data: {"choices":[{"delta":{"content":"Drink "}}]}',
                b"",
                b"data: not-json",
                b'data: {"choices":[{"delta":{"content":"water."}}]}',
                b'data: {"choices":[{"delta":{}}]}',
                b"data: [DONE]",
            ]
        )
    )

    response = client.post(
        "/coach",
        json={
            "userId": "user-1",
            "message": "Any tip?",
            "userProfile": {"goal": "lose weight"},
            "conversationHistory": [{"role": "user", "content": "Hi"}],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)
    assert events[:-1] == [json.dumps({"content": "Drink "}), json.dumps({"content": "water."})]
    assert events[-1] == "[DONE]"

    body = calls[0][1]["json"]
    assert body["stream"] is True
    assert body["messages"][0]["role"] == "system"
    assert "lose weight" in body["messages"][0]["content"]
    assert body["messages"][1] == {"role": "user", "content": "Hi"}
    assert body["messages"][-1] == {"role": "user", "content": "Any tip?"}


def test_coach_reports_upstream_error_in_stream(fake_openrouter):
    fake_openrouter(FakeResponse(status_code=429))

    response = client.post("/coach", json={"userId": "u", "message": "hello"})

    assert response.status_code == 200
    assert _sse_events(response.text) == [json.dumps({"error": "OpenRouter error: 429"})]


def test_coach_requires_api_key(monkeypatch):
    monkeypatch.setattr(coach_main, "OPENROUTER_API_KEY", None)

    response = client.post("/coach", json={"userId": "u", "message": "hello"})

    assert response.status_code == 500
