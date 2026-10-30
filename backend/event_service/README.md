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

## Deployment

### Prerequisites

- Docker installed
- Azure CLI installed and logged in
- Docker Hub account
- OpenRouter API key

### Quick Deploy

1. **Set environment variable:**
```powershell
$env:OPENROUTER_API_KEY = "your-api-key"
```

2. **Run deployment script:**
```powershell
cd backend/event_service
.\deploy.ps1
```

### Manual Deployment

**Build:**
```powershell
docker build -f backend/event_service/Dockerfile -t username/stressoff-event-service:latest .
```

**Push:**
```powershell
docker push username/stressoff-event-service:latest
```

**Deploy to Azure:**
```powershell
az container create \
  --resource-group stressoff-rg \
  --name event-service \
  --image username/stressoff-event-service:latest \
  --dns-name-label eventservice \
  --location norwayeast \
  --cpu 1 --memory 1.5 \
  --ports 8000 \
  --environment-variables OPENROUTER_API_KEY=$env:OPENROUTER_API_KEY \
  --restart-policy Always
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
az container logs --resource-group stressoff-rg --name event-service
```

**Stream logs:**
```powershell
az container logs --resource-group stressoff-rg --name event-service --follow
```

## Integration

Update Flutter app's API configuration:

```dart
// lib/services/api_config.dart
const String eventServiceBaseUrl = 'http://eventservice.norwayeast.azurecontainer.io:8000';
```

Use in Flutter:
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<Map<String, dynamic>> getEventRecommendation({
  required String eventTitle,
  required DateTime startTime,
  required DateTime endTime,
}) async {
  final response = await http.post(
    Uri.parse('$eventServiceBaseUrl/generate-event-recommendation'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'eventTitle': eventTitle,
      'startTime': startTime.toIso8601String(),
      'endTime': endTime.toIso8601String(),
    }),
  );
  
  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  }
  throw Exception('Failed to get recommendation');
}
```
