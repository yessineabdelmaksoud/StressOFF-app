import pytest
from fastapi.testclient import TestClient

from backend.event_service import main as event_main
from backend.tests.conftest import FakeResponse, chat_completion

client = TestClient(event_main.app)

EVENT = {
    "eventTitle": "Team Meeting",
    "startTime": "2025-11-17T14:00:00",
    "endTime": "2025-11-17T15:30:00",
}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "/generate-event-recommendation" in response.json()["endpoints"]


def test_health_reports_openrouter_configuration():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "event-service",
        "openrouter_configured": True,
    }


def test_generate_event_recommendation_formats_response(fake_openrouter):
    calls = fake_openrouter(
        FakeResponse(
            payload=chat_completion(
                {
                    "practices": ["Review the agenda", "Take three deep breaths"],
                    "nutritionSuggestion": "Have a yogurt with nuts.",
                    "purpose": "Align the team on next steps.",
                }
            )
        )
    )

    response = client.post("/generate-event-recommendation", json=EVENT)

    assert response.status_code == 200
    assert response.json() == {
        "eventTitle": "Team Meeting",
        "eventTime": "14:00 - 15:30",
        "practices": "✔️ Review the agenda\n✔️ Take three deep breaths",
        "nutritionSuggestion": "Have a yogurt with nuts.",
        "purpose": "Align the team on next steps.",
    }

    prompt = calls[0][1]["json"]["messages"][0]["content"]
    assert "Duration: 90 minutes" in prompt
    assert "light snack" in prompt  # 14:00 falls in the afternoon snack slot


def test_generate_event_recommendation_defaults_missing_fields(fake_openrouter):
    fake_openrouter(FakeResponse(payload=chat_completion({})))

    response = client.post("/generate-event-recommendation", json=EVENT)

    assert response.status_code == 200
    body = response.json()
    assert body["practices"] == ""
    assert body["nutritionSuggestion"] == ""
    assert body["purpose"] == ""


@pytest.mark.parametrize(
    "upstream",
    [
        FakeResponse(status_code=503, text="unavailable"),
        FakeResponse(payload={"choices": []}),
        FakeResponse(payload=chat_completion("not json")),
    ],
)
def test_generate_event_recommendation_upstream_errors_return_502(fake_openrouter, upstream):
    fake_openrouter(upstream)

    response = client.post("/generate-event-recommendation", json=EVENT)

    assert response.status_code == 502


def test_generate_event_recommendation_validates_request():
    response = client.post(
        "/generate-event-recommendation",
        json={"eventTitle": "No times", "startTime": "not-a-date"},
    )
    assert response.status_code == 422


def test_generate_event_recommendation_requires_api_key(monkeypatch):
    monkeypatch.setattr(event_main, "OPENROUTER_API_KEY", None)

    response = client.post("/generate-event-recommendation", json=EVENT)

    assert response.status_code == 500
