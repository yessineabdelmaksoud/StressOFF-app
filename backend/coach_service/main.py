import json
import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.common.models import CoachingRequest

app = FastAPI(title="StressOFF Coach Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@app.post("/coach")
async def ai_coach(request: CoachingRequest):
    if OPENROUTER_API_KEY is None:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    profile = request.userProfile or {}
    system_prompt = f"""You are a professional AI health coach.
Analyze the user's health and lifestyle data and provide clear, concise, and professional guidance in English.

User Profile:
- Gender: {profile.get('gender', 'Not specified')}
- Weight: {profile.get('weight', 'Not specified')} kg
- Height: {profile.get('height', 'Not specified')} cm
- Goal: {profile.get('goal', 'General wellness')}

Your role:
- Provide personalized nutrition and lifestyle advice and encouragement
- Answer questions about healthy eating, Tunisian cuisine, Mediterranean diet and fitness
- Be positive, warm, supportive, and motivating
- Keep responses concise (2-3 sentences unless more detail is needed)
- Use simple, friendly English

Guidelines:
- Focus on sustainable, healthy habits
- Respect cultural food preferences
- Encourage balanced Mediterranean diet principles
- Be positive and non-judgmental
"""

    messages = [{"role": "system", "content": system_prompt}]
    if request.conversationHistory:
        messages.extend(request.conversationHistory)
    messages.append({"role": "user", "content": request.message})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": True,
    }

    def generate_stream():
        try:
            with requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=data,
                stream=True,
                timeout=60,
            ) as response:
                if not response.ok:
                    error_msg = f"OpenRouter error: {response.status_code}"
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                for line in response.iter_lines():
                    if line:
                        decoded = line.decode("utf-8")
                        if decoded.startswith("data: "):
                            data_str = decoded[6:]
                            if data_str.strip() == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break

                            try:
                                chunk = json.loads(data_str)
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                            except json.JSONDecodeError:
                                continue
        except Exception as exc:
            print("[Coach Service] streaming error:", exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
async def root():
    return {"message": "Coach Service ready", "endpoints": ["/coach"]}

