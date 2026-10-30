# Event Service

AI-powered event recommendation service for the StressOFF application.

## Features

- Generate personalized recommendations for calendar events
- Stress reduction practices based on event context
- Nutrition suggestions aligned with event timing
- Purpose and goal clarity for better preparation

## API Endpoints

### `POST /generate-event-recommendation`

Generate recommendations for a calendar event.

**Request Body:**
```json
{
  "eventTitle": "Team Meeting",
  "startTime": "2025-11-17T14:00:00",
  "endTime": "2025-11-17T15:00:00"
}
```

**Response:**
```json
{
  "eventTitle": "Team Meeting",
  "eventTime": "14:00 - 15:00",
  "practices": "✔️ Take deep breaths\n✔️ Review agenda\n✔️ Stay hydrated",
  "nutritionSuggestion": "Consider a light snack like yogurt or nuts...",
  "purpose": "Stay focused and contribute effectively"
}
```

### `GET /health`

Health check endpoint.

### `GET /`

Service information and available endpoints.

## Run locally

From the repository root:

```bash
pip install -r backend/event_service/requirements.txt
export OPENROUTER_API_KEY=<your-openrouter-key>
uvicorn backend.event_service.main:app --host 0.0.0.0 --port 8003
```

On Windows: `.\backend\start.ps1 -Service event` (also port 8003).

## Deployment

The service is deployed like the other three: one Docker image on Docker Hub, one Azure Container Instance. The container listens on port 8000.

### Prerequisites

- Docker installed
- Azure CLI installed and logged in
- Docker Hub account
- OpenRouter API key

**Build and push** (from the repository root, because the Dockerfile copies `backend/common`):
```bash
docker build -f backend/event_service/Dockerfile -t <dockerhub-user>/event-service:v1.0.0 .
docker login --username <dockerhub-user>
docker push <dockerhub-user>/event-service:v1.0.0
```

**Deploy to Azure:**
```bash
az login
az account set --subscription <subscription-id>
az group create --name stress-rg --location norwayeast

az container create \
  --resource-group stress-rg \
  --name event-service-ci \
  --image <dockerhub-user>/event-service:v1.0.0 \
  --dns-name-label eventservice \
  --ports 8000 \
  --registry-login-server index.docker.io \
  --registry-username <dockerhub-user> \
  --registry-password <dockerhub-token> \
  --secure-environment-variables OPENROUTER_API_KEY=<your-openrouter-key> \
  --os-type Linux --cpu 1 --memory 1.5 \
  --location norwayeast
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes |

## Service URL

After deployment: `http://eventservice.norwayeast.azurecontainer.io:8000`

## Testing

**Health Check:**
```powershell
Invoke-WebRequest -Uri "http://eventservice.norwayeast.azurecontainer.io:8000/health"
```

**Test Event Recommendation:**
```powershell
$body = @{
    eventTitle = "Project Review"
    startTime = "2025-11-17T10:00:00"
    endTime = "2025-11-17T11:00:00"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://eventservice.norwayeast.azurecontainer.io:8000/generate-event-recommendation" -Method POST -Body $body -ContentType "application/json"
```

## Monitoring

**View logs:**
```powershell
az container logs --resource-group stress-rg --name event-service-ci
```

**Stream logs:**
```powershell
az container logs --resource-group stress-rg --name event-service-ci --follow
```

## Integration

The Flutter app calls this service through [`lib/services/event_service.dart`](../../lib/services/event_service.dart), whose base URL comes from `EVENT_SERVICE_URL` in [`lib/services/api_config.dart`](../../lib/services/api_config.dart). Override it at build time:

```bash
flutter run --dart-define=EVENT_SERVICE_URL=http://10.0.2.2:8003
```
