"""Helper functions shared by backend services."""

import json
from io import BytesIO
from typing import List, Optional

from PIL import Image


def coerce_text(value) -> str:
    """Force AI output fields into readable strings."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def compress_image(image_bytes: bytes, max_side: int = 800, quality: int = 75) -> bytes:
    """Downscale large pictures and re-encode as JPEG to stay within model limits."""
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")

            if max(img.size) > max_side:
                img.thumbnail((max_side, max_side))

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            return buffer.getvalue()
    except Exception as exc:
        print("[Backend] image compression skipped:", exc)
    return image_bytes


def create_meal_prompt(
    user_profile: dict,
    meal_type: Optional[str] = None,
    user_allergies: Optional[List[str]] = None,
) -> str:
    """Create a professional English prompt for meal analysis."""

    context = f"""You are a professional AI dietitian specialized in Mediterranean, Tunisian, and French cuisine.
                  Analyze the provided meal image and respond strictly in professional English with clear, accurate, and coherent output.

**Profil Utilisateur** :
- Genre: {user_profile.get('gender', 'Non spécifié')}
- Poids: {user_profile.get('weight', 'Non spécifié')} kg
- Taille: {user_profile.get('height', 'Non spécifié')} cm
- Objectif: {user_profile.get('goal', 'Non spécifié')}
"""

    if user_allergies:
        context += f"- Known allergies: {', '.join(user_allergies)}\n"

    if meal_type:
        meal_types = {
            "breakfast": "Breakfast",
            "lunch": "Lunch",
            "dinner": "Dinner",
            "snack": "Snack",
        }
        context += f"- Meal type: {meal_types.get(meal_type, meal_type)}\n"

    context += """
**Task**:
1. Identify the dish name in English (exact Tunisian name if applicable, otherwise a description, all in english)
2. List main ingredients
3. Estimate macronutrients (typical portions)
4. Provide personalized health advice based on user profile
5. Suggest possible improvements or adjustments
6. Detect if any of the user's known allergies are present. If yes, list them clearly in `allergiesDetected`.

**IMPORTANT**: Return ONLY a strict JSON object without extra text:

{
    "dishName": "Dish name",
    "ingredients": ["ingredient1", "ingredient2", ...],
    "nutrition": {
        "calories": 0,
        "proteins": 0,
        "carbs": 0,
        "fats": 0,
        "fibers": 0
    },
    "healthAdvice": "Personalized health advice",
    "recommendation": "Suggested adjustments",
    "allergiesDetected": ["allergen1", "allergen2"]
}
"""
    return context

