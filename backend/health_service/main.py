import json
import os
from typing import List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.common.models import HealthAnalysisRequest
from backend.common.utils import coerce_text

app = FastAPI(title="StressOFF Health Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _calculate_median(values: List[float]) -> float:
    sorted_values = sorted(values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]


@app.post("/analyze-health")
async def analyze_health(request: HealthAnalysisRequest):
    if OPENROUTER_API_KEY is None:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    try:
        if not request.metrics:
            raise HTTPException(status_code=400, detail="No health metrics provided")

        hrv_values = [m.hrv for m in request.metrics]
        hr_values = [m.heartRate for m in request.metrics]
        resting_hr_values = [m.restingHeartRate for m in request.metrics]
        spo2_values = [m.spo2 for m in request.metrics if m.spo2 is not None]

        median_hrv = _calculate_median(hrv_values)
        avg_resting_hr = sum(resting_hr_values) / len(resting_hr_values)
        avg_spo2 = sum(spo2_values) / len(spo2_values) if spo2_values else None

        total_steps = sum(m.steps for m in request.metrics)
        total_calories = sum(m.calories for m in request.metrics)
        total_active_minutes = sum(m.activeMinutes for m in request.metrics)

        hrv_variance = sum((x - median_hrv) ** 2 for x in hrv_values) / len(hrv_values)
        stress_level = min(10.0, max(0.0, (hrv_variance / 50) + (avg_resting_hr - 60) / 40))

        alerts = []
        if median_hrv < 40:
            alerts.append("HRV is low. Consider recovery protocols.")
        if avg_resting_hr > 75:
            alerts.append("Resting HR is elevated. Monitor hydration and stress.")
        if total_steps < 6000:
            alerts.append("Low activity level detected today.")
        if avg_spo2 and avg_spo2 < 94:
            alerts.append("Blood oxygen average is below 94%.")
        if request.sleepData:
            duration = request.sleepData.durationHours
            if duration < 6:
                alerts.append(f"Sleep duration is short ({duration:.1f}h).")

        profile = request.userProfile or {}
        sleep_info = "Sleep data not available."
        sleep_quality_description = "not available"
        if request.sleepData:
            duration = request.sleepData.durationHours
            score = request.sleepData.qualityScore
            sleep_info = (
                f"- Sleep: {duration:.1f}h, score {score:.0f}/100 "
                f"(deep {request.sleepData.deepSleepMinutes}m, "
                f"REM {request.sleepData.remSleepMinutes}m)"
            )
            if score >= 85 and duration >= 7:
                sleep_quality_description = "excellent and restful"
            elif score >= 70:
                sleep_quality_description = "good"
            elif score >= 50:
                if duration < 6:
                    sleep_quality_description = "short and likely interrupted"
                else:
                    sleep_quality_description = "fair, possibly light"
            else:
                if duration < 5:
                    sleep_quality_description = "very poor and short"
                else:
                    sleep_quality_description = "poor and likely fitful"

        alerts_text = "\n".join(f"- {alert}" for alert in alerts) if alerts else "No critical alerts"

        prompt = f"""You are a health AI coach. Analyze this user's daily health data and provide brief, actionable advice.

**User Profile:**
- Gender: {profile.get('gender', 'Not specified')}
- Weight: {profile.get('weight', 'Not specified')} kg
- Goal: {profile.get('goal', 'General health')}

**Today's Data (24h):**
{sleep_info}
- Resting HR: {avg_resting_hr:.0f} bpm
- HRV median: {median_hrv:.0f} ms
- Total steps: {total_steps:,}
- Calories burned: {total_calories:.0f} kcal
- Active time: {total_active_minutes} min
- Blood oxygen (SpO2): {avg_spo2:.1f}% if avg_spo2 else 'Not available'
- Estimated stress: {stress_level:.1f}/10

**Alerts:**
{alerts_text}

Provide a brief analysis in JSON format:

{{
    "summary": "One sentence describing today's health state",
    "action": "One concrete action to take today",
    "breakfastSuggestion": "Brief breakfast recommendation based on data",
    "indicatorToWatch": "Which metric to monitor (HR, HRV, steps, etc.)",
    "sleepRemark": "A short encouragement sentence for the sleep card",
    "sleepPractices": "2-3 bullet tips for better sleep if needed, else encouragement"
}}
"""

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "qwen/qwen2.5-vl-32b-instruct:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "max_tokens": 400,
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        if not response.ok:
            print("[OpenRouter] analyze-health error:", response.status_code, response.text)
            raise HTTPException(status_code=502, detail="Health analysis service temporarily unavailable")

        result = response.json()
        choices = result.get("choices")
        if not choices:
            raise HTTPException(status_code=502, detail="Invalid response from health analysis service")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise HTTPException(status_code=502, detail="Empty response from health analysis service")

        analysis = json.loads(content)

        return {
            "summary": coerce_text(analysis.get("summary")),
            "action": coerce_text(analysis.get("action")),
            "breakfastSuggestion": coerce_text(analysis.get("breakfastSuggestion")),
            "indicatorToWatch": coerce_text(analysis.get("indicatorToWatch")),
            "sleepRemark": coerce_text(analysis.get("sleepRemark")),
            "sleepPractices": coerce_text(analysis.get("sleepPractices")),
            "alerts": alerts,
            "dailyStats": {
                "avgRestingHR": round(avg_resting_hr, 1),
                "medianHRV": round(median_hrv, 1),
                "totalSteps": total_steps,
                "totalCalories": round(total_calories, 1),
                "totalActiveMinutes": total_active_minutes,
                "avgSpO2": round(avg_spo2, 1) if avg_spo2 else None,
                "stressLevel": round(stress_level, 1),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        print("[Health Service] analyze-health error:", exc)
        raise HTTPException(status_code=500, detail=f"Health analysis failed: {str(exc)}")


@app.get("/")
async def root():
    return {"message": "Health Service ready", "endpoints": ["/analyze-health"]}
