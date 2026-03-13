import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';

/// Consent-aware analytics service wrapping self-hosted Umami.
///
/// Events are only sent after the user explicitly grants consent, satisfying
/// DSGVO/GDPR requirements. All data stays on your own infrastructure.
class AnalyticsService {
  AnalyticsService();

  bool _consentGranted = false;

  /// Whether the user has granted analytics consent.
  bool get consentGranted => _consentGranted;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  /// Initialize the analytics service.
  ///
  /// Restores the previous consent state from SharedPreferences.
  Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _consentGranted =
          prefs.getBool(AppConfig.consentAnalyticsKey) ?? false;
    } catch (_) {
      // Graceful degradation -- analytics failure must never crash the app.
      _consentGranted = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Consent management
  // ---------------------------------------------------------------------------

  /// Check whether analytics consent has been stored locally.
  Future<bool> hasConsent() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(AppConfig.consentAnalyticsKey) ?? false;
  }

  /// Grant analytics consent -- enables Umami event tracking and persists the
  /// preference to SharedPreferences.
  Future<void> grantConsent() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConfig.consentAnalyticsKey, true);
    _consentGranted = true;
  }

  /// Revoke analytics consent -- disables tracking.
  Future<void> revokeConsent() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConfig.consentAnalyticsKey, false);
    _consentGranted = false;
  }

  // ---------------------------------------------------------------------------
  // Tracking helpers
  // ---------------------------------------------------------------------------

  /// Track a named event via the Umami HTTP API. Events are silently dropped
  /// when consent has not been granted or Umami is not configured.
  Future<void> trackEvent(
    String name, {
    Map<String, dynamic>? properties,
  }) async {
    if (!_consentGranted) return;

    final host = AppConfig.umamiHost;
    final websiteId = AppConfig.umamiWebsiteId;
    if (host.isEmpty || websiteId.isEmpty) return;

    try {
      await http.post(
        Uri.parse('$host/api/send'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'payload': {
            'website': websiteId,
            'name': name,
            'data': properties ?? {},
            'url': '/',
          },
          'type': 'event',
        }),
      );
    } catch (_) {
      // Silently fail -- analytics should never crash the app.
    }
  }

  /// Track a screen view.
  Future<void> trackScreen(String screenName) async {
    await trackEvent('screen_view', properties: {'screen': screenName});
  }
}
