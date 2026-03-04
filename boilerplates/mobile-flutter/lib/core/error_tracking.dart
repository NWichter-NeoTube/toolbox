import 'package:flutter/foundation.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';

/// Consent-aware wrapper around self-hosted Sentry for error tracking.
///
/// User context is only attached after the user grants error-tracking consent
/// (DSGVO/GDPR compliance).
class ErrorTrackingService {
  ErrorTrackingService();

  bool _initialized = false;
  bool _consentGranted = false;

  /// Whether Sentry has been initialized.
  bool get isInitialized => _initialized;

  /// Whether the user has granted error-tracking consent.
  bool get consentGranted => _consentGranted;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  /// Initialize Sentry Flutter.
  ///
  /// This should be called **before** `runApp` — see `main.dart` for the
  /// canonical pattern using [SentryFlutter.init].
  ///
  /// After initialization the service checks SharedPreferences for a stored
  /// consent preference.
  Future<void> init({required String dsn}) async {
    if (dsn.isEmpty) return;

    _initialized = true;

    final prefs = await SharedPreferences.getInstance();
    _consentGranted =
        prefs.getBool(AppConfig.consentErrorTrackingKey) ?? false;

    if (!_consentGranted) {
      // Clear any user scope that may have leaked.
      Sentry.configureScope((scope) => scope.setUser(null));
    }
  }

  // ---------------------------------------------------------------------------
  // Consent management
  // ---------------------------------------------------------------------------

  /// Grant error-tracking consent — allows user context to be attached to
  /// Sentry events.
  Future<void> grantConsent() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConfig.consentErrorTrackingKey, true);
    _consentGranted = true;
  }

  /// Revoke error-tracking consent — removes user context from Sentry.
  Future<void> revokeConsent() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConfig.consentErrorTrackingKey, false);
    _consentGranted = false;

    Sentry.configureScope((scope) => scope.setUser(null));
  }

  /// Check locally stored consent preference.
  Future<bool> hasConsent() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(AppConfig.consentErrorTrackingKey) ?? false;
  }

  // ---------------------------------------------------------------------------
  // Tracking helpers
  // ---------------------------------------------------------------------------

  /// Capture an exception in Sentry.
  Future<void> captureException(
    dynamic exception, {
    dynamic stackTrace,
  }) async {
    if (!_initialized) return;

    try {
      await Sentry.captureException(
        exception,
        stackTrace: stackTrace,
      );
    } catch (e) {
      debugPrint('ErrorTrackingService: failed to capture exception — $e');
    }
  }

  /// Add a breadcrumb for debugging context.
  void addBreadcrumb(String message, {String? category}) {
    if (!_initialized) return;

    try {
      Sentry.addBreadcrumb(
        Breadcrumb(
          message: message,
          category: category ?? 'app',
          timestamp: DateTime.now(),
        ),
      );
    } catch (_) {
      // Non-critical.
    }
  }

  /// Set the user context on Sentry (only if consent was granted).
  void setUser({required String id, String? email}) {
    if (!_initialized || !_consentGranted) return;

    Sentry.configureScope(
      (scope) => scope.setUser(
        SentryUser(id: id, email: email),
      ),
    );
  }
}
