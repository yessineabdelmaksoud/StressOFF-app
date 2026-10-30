import base64
import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.meal_service import main as meal_main
from backend.tests.conftest import FakeResponse, chat_completion

client = TestClient(meal_main.app)

MEAL_RESULT = {
    "dishName": "Couscous",
    "ingredients": ["semolina", "lamb", "carrots"],
    "nutrition": {"calories": 650, "proteins": 30, "carbs": 80, "fats": 20, "fibers": 8},
    "healthAdvice": "Balanced meal.",
    "recommendation": "Add more vegetables.",
    "allergiesDetected": ["gluten"],
}


def _meal(meal_type, dish, calories, proteins=10, carbs=20, fats=5, fibers=2):
    return {
        "userId": "user-1",
        "mealType": meal_type,
        "timestamp": f"2025-11-17T{12 if meal_type == 'lunch' else 8}:00:00",
        "dishName": dish,
        "ingredients": ["x"],
        "nutrition": {
            "calories": calories,
            "proteins": proteins,
            "carbs": carbs,
            "fats": fats,
            "fibers": fibers,
        },
        "healthAdvice": "ok",
        "recommendation": "ok",
    }


def _jpeg_upload(size=(1200, 900)):
    buffer = BytesIO()
    Image.new("RGB", size, color=(10, 120, 30)).save(buffer, format="JPEG")
    return ("meal.jpg", buffer.getvalue(), "image/jpeg")


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["endpoints"] == ["/analyze-meal", "/analyze-daily"]


def test_analyze_meal_returns_model_json_and_sends_compressed_image(fake_openrouter):
    calls = fake_openrouter(FakeResponse(payload=chat_completion(MEAL_RESULT)))

    response = client.post(
        "/analyze-meal",
        files={"image": _jpeg_upload()},
        data={
            "userId": "user-1",
            "mealType": "lunch",
            "userProfile": json.dumps({"weight": 70, "allergies": ["gluten"]}),
        },
    )

    assert response.status_code == 200
    assert response.json() == MEAL_RESULT

    assert len(calls) == 1
    url, kwargs = calls[0]
    assert url == meal_main.OPENROUTER_URL
    body = kwargs["json"]
    assert body["response_format"] == {"type": "json_object"}
    text_part, image_part = body["messages"][0]["content"]
    assert "Known allergies: gluten" in text_part["text"]
    data_url = image_part["image_url"]["url"]
    assert data_url.startswith("data:image/jpeg;base64,")
    sent = base64.b64decode(data_url.split(",", 1)[1])
    with Image.open(BytesIO(sent)) as img:
        assert max(img.size) == 800


def test_analyze_meal_maps_rate_limit_to_429(fake_openrouter):
    fake_openrouter(FakeResponse(status_code=429, text="rate limited"))

    response = client.post(
        "/analyze-meal", files={"image": _jpeg_upload((50, 50))}, data={"userId": "u"}
    )

    assert response.status_code == 429


@pytest.mark.parametrize(
    "upstream, expected_status",
    [
        (FakeResponse(status_code=503, text="down"), 502),
        (FakeResponse(payload={"error": {"message": "bad model"}}), 502),
        (FakeResponse(payload=chat_completion("not json")), 500),
    ],
)
def test_analyze_meal_upstream_errors(fake_openrouter, upstream, expected_status):
    fake_openrouter(upstream)

    response = client.post(
        "/analyze-meal", files={"image": _jpeg_upload((50, 50))}, data={"userId": "u"}
    )

    assert response.status_code == expected_status


def test_analyze_meal_requires_api_key(monkeypatch):
    monkeypatch.setattr(meal_main, "OPENROUTER_API_KEY", None)

    response = client.post(
        "/analyze-meal", files={"image": _jpeg_upload((50, 50))}, data={"userId": "u"}
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "OPENROUTER_API_KEY not configured"


def test_analyze_daily_computes_totals_and_normalizes_ai_fields(fake_openrouter):
    fake_openrouter(
        FakeResponse(
            payload=chat_completion(
                {
                    "globalAdvice": ["Good protein.", "Low fiber."],
                    "recommendations": {"dinner": "Add salad"},
                    "needsMet": "Yes",
                }
            )
        )
    )

    response = client.post(
        "/analyze-daily",
        json={
            "userId": "user-1",
            "date": "2025-11-17",
            "meals": [
                _meal("breakfast", "Oatmeal", 350, proteins=12, fibers=6),
                _meal("lunch", "Couscous", 650, proteins=30, fibers=8),
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user-1_2025-11-17"
    assert body["totalNutrition"]["calories"] == 1000
    assert body["totalNutrition"]["proteins"] == 42
    assert body["totalNutrition"]["fibers"] == 14
    assert body["globalAdvice"] == "Good protein. Low fiber."
    assert body["recommendations"] == '{"dinner": "Add salad"}'
    assert body["needsMet"] is True
    assert len(body["mealAnalysisIds"]) == 2


def test_analyze_daily_rejects_invalid_payload():
    response = client.post("/analyze-daily", json={"userId": "u", "date": "2025-11-17"})
    assert response.status_code == 422
