import pytest
from fastapi.testclient import TestClient

from backend.health_service import main as health_main
from backend.tests.conftest import FakeResponse, chat_completion

client = TestClient(health_main.app)

AI_ANALYSIS = {
    "summary": "Elevated stress today.",
    "action": "Take a 20 minute walk.",
    "breakfastSuggestion": "Oatmeal with fruit.",
    "indicatorToWatch": "HRV",
    "sleepRemark": "Short night, rest early.",
    "sleepPractices": ["No screens after 22:00.", "Keep the room cool."],
}


def _metric(hour, heart_rate, resting, hrv, steps, spo2=97.0):
    return {
        "timestamp": f"2025-11-17T{hour:02d}:00:00",
        "heartRate": heart_rate,
        "restingHeartRate": resting,
        "hrv": hrv,
        "steps": steps,
        "calories": 100.0,
        "activeMinutes": 10,
        "spo2": spo2,
    }


@pytest.mark.parametrize(
    "values, expected",
    [([3.0, 1.0, 2.0], 2.0), ([4.0, 1.0, 3.0, 2.0], 2.5), ([5.0], 5.0)],
)
def test_calculate_median(values, expected):
    assert health_main._calculate_median(values) == expected


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["endpoints"] == ["/analyze-health"]


def test_analyze_health_computes_stats_alerts_and_normalizes_ai_text(fake_openrouter):
    calls = fake_openrouter(FakeResponse(payload=chat_completion(AI_ANALYSIS)))

    response = client.post(
        "/analyze-health",
        json={
            "userId": "user-1",
            "date": "2025-11-17",
            "metrics": [
                _metric(8, 90, 78, 30, 1500, spo2=93.0),
                _metric(12, 95, 80, 35, 1500, spo2=93.0),
                _metric(18, 85, 76, 40, 1000, spo2=94.0),
            ],
            "sleepData": {
                "durationHours": 5.5,
                "qualityScore": 55,
                "deepSleepMinutes": 40,
                "remSleepMinutes": 60,
                "lightSleepMinutes": 230,
            },
            "userProfile": {"gender": "male", "weight": 80},
        },
    )

    assert response.status_code == 200
    body = response.json()

    stats = body["dailyStats"]
    assert stats["avgRestingHR"] == 78.0
    assert stats["medianHRV"] == 35.0
    assert stats["totalSteps"] == 4000
    assert stats["totalCalories"] == 300.0
    assert stats["totalActiveMinutes"] == 30
    assert stats["avgSpO2"] == 93.3
    assert 0 <= stats["stressLevel"] <= 10

    assert body["alerts"] == [
        "HRV is low. Consider recovery protocols.",
        "Resting HR is elevated. Monitor hydration and stress.",
        "Low activity level detected today.",
        "Blood oxygen average is below 94%.",
        "Sleep duration is short (5.5h).",
    ]

    assert body["summary"] == "Elevated stress today."
    assert body["sleepPractices"] == "No screens after 22:00. Keep the room cool."

    prompt = calls[0][1]["json"]["messages"][0]["content"]
    assert "Total steps: 4,000" in prompt
    assert "Sleep: 5.5h, score 55/100" in prompt


def test_analyze_health_rejects_empty_metrics():
    response = client.post(
        "/analyze-health", json={"userId": "u", "date": "2025-11-17", "metrics": []}
    )
    assert response.status_code == 400


def test_analyze_health_upstream_error_returns_502(fake_openrouter):
    fake_openrouter(FakeResponse(status_code=500, text="boom"))

    response = client.post(
        "/analyze-health",
        json={"userId": "u", "date": "2025-11-17", "metrics": [_metric(8, 70, 60, 60, 8000)]},
    )

    assert response.status_code == 502
