"""Pydantic models shared across backend microservices."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class Nutrition(BaseModel):
    calories: float
    proteins: float
    carbs: float
    fats: float
    fibers: float


class MealAnalysis(BaseModel):
    userId: str
    mealType: str
    timestamp: str
    dishName: str
    ingredients: List[str]
    nutrition: Nutrition
    healthAdvice: str
    recommendation: str
    allergiesDetected: Optional[List[str]] = []


class DailyAnalysisRequest(BaseModel):
    userId: str
    date: str
    meals: List[MealAnalysis]


class CoachingRequest(BaseModel):
    userId: str
    message: str
    userProfile: Optional[Dict] = None
    conversationHistory: Optional[List[Dict]] = None


class HealthMetric(BaseModel):
    timestamp: str
    heartRate: float
    restingHeartRate: float
    hrv: float
    steps: int
    calories: float
    activeMinutes: int
    spo2: Optional[float] = None


class SleepData(BaseModel):
    durationHours: float
    qualityScore: float
    deepSleepMinutes: int
    remSleepMinutes: int
    lightSleepMinutes: int


class HealthAnalysisRequest(BaseModel):
    userId: str
    date: str
    metrics: List[HealthMetric]
    sleepData: Optional[SleepData] = None
    userProfile: Optional[Dict] = None


class EventRequest(BaseModel):
    eventTitle: str
    startTime: datetime
    endTime: datetime


class EventRecommendationResponse(BaseModel):
    eventTitle: str
    eventTime: str
    practices: str
    nutritionSuggestion: str
    purpose: str

