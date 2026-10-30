// JSON parsing tests for the health models returned by the backend
// and stored in Firestore. No Firebase initialization is needed.

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:stressoff/models/health_models.dart';

void main() {
  test('EventRecommendation.fromJson reads the event service response', () {
    final rec = EventRecommendation.fromJson({
      'eventTitle': 'Team Meeting',
      'eventTime': '14:00 - 15:00',
      'practices': '✔️ Take deep breaths\n✔️ Review agenda',
      'nutritionSuggestion': 'A light snack like yogurt or nuts.',
      'purpose': 'Stay focused and contribute effectively',
    });

    expect(rec.eventTitle, 'Team Meeting');
    expect(rec.eventTime, '14:00 - 15:00');
    expect(rec.practices, contains('Review agenda'));
    expect(rec.nutritionSuggestion, startsWith('A light snack'));
    expect(rec.purpose, 'Stay focused and contribute effectively');
  });

  test('EventRecommendation.fromJson defaults missing fields to empty strings', () {
    final rec = EventRecommendation.fromJson({'eventTitle': 'Standup'});

    expect(rec.eventTitle, 'Standup');
    expect(rec.eventTime, '');
    expect(rec.practices, '');
    expect(rec.nutritionSuggestion, '');
    expect(rec.purpose, '');
  });

  test('HealthMetrics round-trips through toJson/fromJson', () {
    final original = HealthMetrics(
      id: 'm1',
      userId: 'u1',
      timestamp: DateTime(2025, 11, 17, 8, 30),
      heartRate: 72.5,
      restingHeartRate: 61,
      hrv: 48,
      steps: 1200,
      calories: 85.2,
      activeMinutes: 12,
      spo2: 97,
    );

    final parsed = HealthMetrics.fromJson(original.toJson());

    expect(parsed.id, 'm1');
    expect(parsed.timestamp, DateTime(2025, 11, 17, 8, 30));
    expect(parsed.heartRate, 72.5);
    expect(parsed.steps, 1200);
    expect(parsed.spo2, 97.0);
  });

  test('HealthMetrics.fromJson converts ints to doubles and accepts Timestamps', () {
    final parsed = HealthMetrics.fromJson({
      'timestamp': Timestamp.fromDate(DateTime(2025, 1, 2, 3, 4)),
      'heartRate': 80,
      'restingHeartRate': 60,
      'hrv': 50,
      'steps': 10,
      'calories': 5,
      'activeMinutes': 1,
    });

    expect(parsed.timestamp, DateTime(2025, 1, 2, 3, 4));
    expect(parsed.heartRate, isA<double>());
    expect(parsed.calories, 5.0);
    expect(parsed.spo2, isNull);
    expect(parsed.id, '');
  });

  test('SleepData.fromJson parses an ISO date string', () {
    final sleep = SleepData.fromJson({
      'date': '2025-11-17T00:00:00.000',
      'durationHours': 7,
      'qualityScore': 82,
      'deepSleepMinutes': 75,
      'remSleepMinutes': 95,
      'lightSleepMinutes': 250,
    });

    expect(sleep.date, DateTime(2025, 11, 17));
    expect(sleep.durationHours, 7.0);
    expect(sleep.qualityScore, 82.0);
    expect(sleep.deepSleepMinutes, 75);
  });
}
