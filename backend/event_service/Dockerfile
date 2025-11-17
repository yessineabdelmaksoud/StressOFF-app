FROM python:3.12-slim

WORKDIR /app

# Copy common models and utils
COPY backend/common ./backend/common

# Copy event service code
COPY backend/event_service ./backend/event_service

# Install dependencies
RUN pip install --no-cache-dir -r backend/event_service/requirements.txt

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.event_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
