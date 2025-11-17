FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/common ./backend/common
COPY backend/meal_service ./backend/meal_service

RUN pip install --no-cache-dir -r backend/meal_service/requirements.txt

EXPOSE 8000

CMD ["uvicorn", "backend.meal_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
