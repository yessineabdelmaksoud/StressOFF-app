import json
import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.common.models import EventRecommendationResponse, EventRequest

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = FastAPI(title="StressOFF Event Service")
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
# Event recommendation endpoint
# ---------------------------------------------------------------------------
@app.post("/generate-event-recommendation", response_model=EventRecommendationResponse)
async def generate_event_recommendation(request: EventRequest):
    """
    Generate AI-powered recommendations for calendar events.
    
    Provides:
    - Stress reduction practices
    - Nutrition suggestions based on event timing
    - Purpose and goals for the event
    """
    event_title = request.eventTitle
    start_time = request.startTime
    end_time = request.endTime
    hour = start_time.hour
    duration_minutes = (end_time - start_time).total_seconds() / 60

    if OPENROUTER_API_KEY is None:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    # Determine meal type based on event time
    if hour < 12:
        meal_type = "nutritious breakfast"
        meal_examples = "eggs, oatmeal, fresh fruits, yogurt"
    elif hour < 14:
        meal_type = "balanced lunch"
        meal_examples = "lean protein, whole grains, vegetables"
    elif hour < 17:
        meal_type = "light snack"
        meal_examples = "yogurt, fruit, nuts, energy bar"
    else:
        meal_type = "light evening snack"
        meal_examples = "calming tea, whole grain biscuit"

    # Prepare AI prompt
    prompt = f"""You are a mindful productivity and wellness assistant. Based on the calendar event below,
provide practical recommendations to help the user stay focused, reduce stress, and maintain energy.

**Event Details**:
- Title: {event_title}
- Time: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}
- Duration: {int(duration_minutes)} minutes
- Suggested meal/snack: {meal_type}
- Examples: {meal_examples}

**Instructions**:
Return ONLY valid JSON with these fields:
{{
  "practices": ["2-3 practical tips for focus and stress reduction before this event"],
  "nutritionSuggestion": "One concise paragraph suggesting the best {meal_type} to optimize energy and focus",
  "purpose": "One clear sentence describing the main objective for this event"
}}

Keep the response professional, concise, and actionable.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "qwen/qwen2.5-vl-32b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    # Call OpenRouter API
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    
    if not response.ok:
        print(
            "[OpenRouter] generate-event-recommendation error:",
            response.status_code,
            response.text,
        )
        raise HTTPException(status_code=502, detail="OpenRouter provider error")

    try:
        result_json = response.json()
        choices = result_json.get("choices", [])
        
        if not choices:
            raise HTTPException(status_code=502, detail="No choices returned by OpenRouter")
        
        content_str = choices[0]["message"]["content"]
        result = json.loads(content_str)

    except json.JSONDecodeError as exc:
        print("[OpenRouter] JSON parse error:", exc)
        raise HTTPException(status_code=502, detail="Invalid response from OpenRouter")

    # Format practices with bullet points
    practices_list = result.get("practices", [])
    formatted_practices = "\n".join([f"✔️ {p}" for p in practices_list])

    return EventRecommendationResponse(
        eventTitle=event_title,
        eventTime=f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
        practices=formatted_practices,
        nutritionSuggestion=result.get("nutritionSuggestion", ""),
        purpose=result.get("purpose", ""),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "event-service",
        "openrouter_configured": OPENROUTER_API_KEY is not None
    }


@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "StressOFF Event Service",
        "version": "1.0.0",
        "endpoints": {
            "/generate-event-recommendation": "POST - Generate event recommendations",
            "/health": "GET - Health check",
            "/": "GET - Service info"
        }
    }
