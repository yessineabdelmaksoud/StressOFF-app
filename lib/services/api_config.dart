/// Central place to configure backend service URLs.
/// Override with `--dart-define=MEAL_SERVICE_URL=https://...` when building.

const String mealServiceBaseUrl = String.fromEnvironment(
  'MEAL_SERVICE_URL',
  defaultValue: 'http://meal-service-yessine-eu.norwayeast.azurecontainer.io:8000',
);

const String coachServiceBaseUrl = String.fromEnvironment(
  'COACH_SERVICE_URL',
  defaultValue: 'http://coach-service-yessine-eu.norwayeast.azurecontainer.io:8000',
);

const String healthServiceBaseUrl = String.fromEnvironment(
  'HEALTH_SERVICE_URL',
  defaultValue: 'http://health-service-yessine-eu.norwayeast.azurecontainer.io:8000',
);

const String eventServiceBaseUrl = String.fromEnvironment(
  'EVENT_SERVICE_URL',
  defaultValue: 'http://eventservice.norwayeast.azurecontainer.io:8003',
);
