/// Event Service - Handles AI-powered event recommendations
/// Provides stress reduction practices, nutrition suggestions, and goal clarity
/// for calendar events.

import 'package:http/http.dart' as http;
import 'dart:convert';
import 'api_config.dart';

class EventService {
  static const String baseUrl = eventServiceBaseUrl;

  /// Generate AI-powered recommendations for a calendar event
  /// 
  /// Returns a Map containing:
  /// - eventTitle: The event name
  /// - eventTime: Formatted time string
  /// - practices: Stress reduction tips (with checkmarks)
  /// - nutritionSuggestion: Meal/snack recommendations
  /// - purpose: Main objective for the event
  static Future<Map<String, dynamic>> generateEventRecommendation({
    required String eventTitle,
    required DateTime startTime,
    required DateTime endTime,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/generate-event-recommendation');

      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'eventTitle': eventTitle,
          'startTime': startTime.toIso8601String(),
          'endTime': endTime.toIso8601String(),
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        String message = 'Error (${response.statusCode})';
        try {
          final data = jsonDecode(response.body);
          if (data is Map && data['detail'] != null) {
            message = data['detail'].toString();
          }
        } catch (_) {}
        throw Exception(message);
      }
    } catch (e) {
      throw Exception('Error generating event recommendation: $e');
    }
  }

  /// Check if the event service is healthy and available
  static Future<bool> checkHealth() async {
    try {
      final uri = Uri.parse('$baseUrl/health');
      final response = await http.get(uri);
      return response.statusCode == 200;
    } catch (e) {
      print('Event service health check failed: $e');
      return false;
    }
  }
}
