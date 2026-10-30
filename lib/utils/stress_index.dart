/// Stress index computation used by the healthcare dashboard.
/// Kept free of Flutter and Firebase calls so it can be unit tested.

import '../models/health_models.dart';

/// Compute stress index (0-100) from heart rate, sleep, and activity
int calculateStressIndex(List<HealthMetrics> metrics, SleepData? sleep) {
  if (metrics.isEmpty) return 0;

  int stressScore = 0;

  /// Heart rate analysis
  final avgHR = metrics.map((m) => m.heartRate).reduce((a, b) => a + b) / metrics.length;
  if (avgHR > 100) {
    stressScore += 30;
  } else if (avgHR > 80) {
    stressScore += 15;
  } else {
    stressScore += 5;
  }

  /// Sleep analysis
  if (sleep != null) {
    if (sleep.qualityScore < 50) {
      stressScore += 30;
    } else if (sleep.qualityScore < 70) {
      stressScore += 15;
    } else {
      stressScore += 5;
    }
  }

  // Activity analysis
  final totalSteps = metrics.fold<int>(0, (sum, m) => sum + m.steps);
  if (totalSteps < 3000) {
    stressScore += 20; // Insuffisant
  } else if (totalSteps > 20000) {
    stressScore += 10; // Suractivité
  } else {
    stressScore += 5; // Bon
  }

  return (stressScore * 0.7).toInt().clamp(0, 100);
}
