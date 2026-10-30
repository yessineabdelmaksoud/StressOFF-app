// Unit tests for the 0-100 stress index shown on the healthcare page.
// Pure Dart logic: no widgets are pumped and Firebase is never initialized.

import 'package:flutter_test/flutter_test.dart';
import 'package:stressoff/models/health_models.dart';
import 'package:stressoff/utils/stress_index.dart';

HealthMetrics _metric({required double heartRate, required int steps}) {
  return HealthMetrics(
    id: 'm',
    userId: 'u',
    timestamp: DateTime(2025, 1, 1, 12),
    heartRate: heartRate,
    restingHeartRate: 60,
    hrv: 50,
    steps: steps,
    calories: 0,
    activeMinutes: 0,
  );
}

SleepData _sleep(double qualityScore) {
  return SleepData(
    id: 's',
    userId: 'u',
    date: DateTime(2025, 1, 1),
    durationHours: 7,
    qualityScore: qualityScore,
    deepSleepMinutes: 60,
    remSleepMinutes: 90,
    lightSleepMinutes: 270,
  );
}

void main() {
  group('calculateStressIndex', () {
    test('returns 0 when there are no metrics', () {
      expect(calculateStressIndex([], _sleep(30)), 0);
    });

    test('calm day: normal heart rate, good sleep, healthy steps', () {
      final metrics = [
        _metric(heartRate: 65, steps: 4000),
        _metric(heartRate: 75, steps: 4000),
      ];
      // (5 + 5 + 5) * 0.7 = 10.5 -> 10
      expect(calculateStressIndex(metrics, _sleep(85)), 10);
    });

    test('averages heart rate across all metrics', () {
      // Average is 90 bpm (> 80), so the moderate heart-rate weight applies.
      final metrics = [
        _metric(heartRate: 70, steps: 2500),
        _metric(heartRate: 110, steps: 2500),
      ];
      // (15 + 15 + 5) * 0.7 = 24.5 -> 24
      expect(calculateStressIndex(metrics, _sleep(60)), 24);
    });

    test('ignores sleep when no sleep data is available', () {
      final metrics = [_metric(heartRate: 105, steps: 1000)];
      // (30 + 20) * 0.7 = 35
      expect(calculateStressIndex(metrics, null), 35);
    });

    test('penalizes very high step counts less than inactivity', () {
      final overActive = [_metric(heartRate: 70, steps: 25000)];
      final inactive = [_metric(heartRate: 70, steps: 500)];
      // (5 + 5 + 10) * 0.7 = 14 and (5 + 5 + 20) * 0.7 = 21
      expect(calculateStressIndex(overActive, _sleep(90)), 14);
      expect(calculateStressIndex(inactive, _sleep(90)), 21);
    });

    test('worst case: high heart rate, poor sleep, inactivity', () {
      final metrics = [_metric(heartRate: 120, steps: 100)];
      // (30 + 30 + 20) * 0.7 = 56, the highest value the formula can produce.
      expect(calculateStressIndex(metrics, _sleep(20)), 56);
    });
  });
}
