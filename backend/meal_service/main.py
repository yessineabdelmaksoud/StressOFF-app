import base64
import json
import os
from typing import Optional

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.common.models import DailyAnalysisRequest
from backend.common.utils import coerce_text, compress_image, create_meal_prompt

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = FastAPI(title="StressOFF Meal Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ---------------------------------------------------------------------------
# Meal analysis
# ---------------------------------------------------------------------------
@app.post("/analyze-meal")
async def analyze_meal(
    image: UploadFile = File(...),
    userId: str = Form(...),
    mealType: Optional[str] = Form(None),
    userProfile: Optional[str] = Form(None),
):
    if OPENROUTER_API_KEY is None:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    try:
        image_data = await image.read()
        compressed_image_data = compress_image(image_data)
        if len(compressed_image_data) != len(image_data):
            print(
                "[Meal Service] image compressed from",
                len(image_data),
                "to",
                len(compressed_image_data),
                "bytes",
            )
        image_base64 = base64.b64encode(compressed_image_data).decode("utf-8")

        profile = json.loads(userProfile) if userProfile else {}
        user_allergies = profile.get("allergies", [])
        prompt_text = create_meal_prompt(profile, mealType, user_allergies)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                        },
                    },
                ],
            }
        ]

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": "qwen/qwen2.5-vl-32b-instruct:free",
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        if not response.ok:
            print("[OpenRouter] analyze-meal error:", response.status_code, response.text)
            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "The analysis service is temporarily overloaded. "
                        "Please try again later or use your own OpenRouter key."
                    ),
                )
            raise HTTPException(status_code=502, detail="OpenRouter provider error. Please try again later.")

        result = response.json()
        choices = result.get("choices")
        if not choices:
            print("[OpenRouter] analyze-meal unexpected payload:", result)
            detail = result.get("error", {}).get("message") if isinstance(result, dict) else None
            raise HTTPException(
                status_code=502,
                detail=detail or "Unexpected response from OpenRouter.",
            )
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        analysis_text = (message or {}).get("content") if isinstance(message, dict) else None
        if not analysis_text:
            print("[OpenRouter] analyze-meal missing content:", result)
            raise HTTPException(status_code=502, detail="Empty response from OpenRouter.")

        return json.loads(analysis_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"JSON decode error: {str(exc)}")
    except HTTPException:
        raise
    except Exception as exc:
        print("[Meal Service] analyze-meal exception:", str(exc))
        raise HTTPException(status_code=500, detail=f"Meal analysis failed: {str(exc)}")


# ---------------------------------------------------------------------------
# Daily meal summary
# ---------------------------------------------------------------------------
@app.post("/analyze-daily")
async def analyze_daily(request: DailyAnalysisRequest):
    if OPENROUTER_API_KEY is None:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    try:
        total_calories = sum(meal.nutrition.calories for meal in request.meals)
        total_proteins = sum(meal.nutrition.proteins for meal in request.meals)
        total_carbs = sum(meal.nutrition.carbs for meal in request.meals)
        total_fats = sum(meal.nutrition.fats for meal in request.meals)
        total_fibers = sum(meal.nutrition.fibers for meal in request.meals)

        meals_summary = "\n".join(
            [
                f"- {meal.mealType}: {meal.dishName} ({meal.nutrition.calories:.0f} kcal)"
                for meal in request.meals
            ]
        )
        prompt = f"""You are a professional AI nutritionist.
Analyze the following daily meals and provide a detailed nutritional summary in professional English.

**Daily Meals**:
{meals_summary}

**Total Nutrition**:
- Calories: {total_calories:.0f} kcal
- Proteins: {total_proteins:.1f}g
- Carbs: {total_carbs:.1f}g
- Fats: {total_fats:.1f}g
- Fibers: {total_fibers:.1f}g

**Recommended Daily Targets**:
- Calories: 2000 kcal
- Proteins: 60g
- Carbs: 250g
- Fats: 70g
- Fibers: 30g

Return ONLY JSON:
{{
    "globalAdvice": "summary",
    "recommendations": "tips",
    "needsMet": true/false
}}
"""

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": "qwen/qwen2.5-vl-32b-instruct:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        choices = result.get("choices")
        if not choices:
            raise HTTPException(status_code=502, detail="Unexpected response from OpenRouter.")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise HTTPException(status_code=502, detail="Empty response from OpenRouter.")

        daily_analysis = json.loads(content)
        needs_met = daily_analysis.get("needsMet", False)
        if isinstance(needs_met, str):
            needs_met = needs_met.strip().lower() in {"true", "oui", "yes", "1"}

        summary = {
            "id": f"{request.userId}_{request.date}",
            "userId": request.userId,
            "date": request.date,
            "mealAnalysisIds": [str(meal.timestamp) for meal in request.meals],
            "totalNutrition": {
                "calories": total_calories,
                "proteins": total_proteins,
                "carbs": total_carbs,
                "fats": total_fats,
                "fibers": total_fibers,
            },
            "globalAdvice": coerce_text(daily_analysis.get("globalAdvice")),
            "recommendations": coerce_text(daily_analysis.get("recommendations")),
            "needsMet": bool(needs_met),
        }
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Daily analysis failed: {str(exc)}")


@app.get("/")
async def root():
    return {
        "message": "Meal Service ready",
        "endpoints": ["/analyze-meal", "/analyze-daily"],
    }

