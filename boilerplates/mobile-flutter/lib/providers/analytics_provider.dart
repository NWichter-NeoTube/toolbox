import 'package:flutter/foundation.dart';

import '../core/analytics.dart';
import '../core/error_tracking.dart';

/// [ChangeNotifier] provider that wraps [AnalyticsService] and
/// [ErrorTrackingService], exposing consent state to the widget tree.
///
/// Listeners are notified whenever the consent state changes so that the UI
/// can react accordingly (e.g. toggle switches in settings).
class AnalyticsProvider extends ChangeNotifier {
  AnalyticsProvider({
    required AnalyticsService analyticsService,
    required ErrorTrackingService errorTrackingService,
  })  : _analytics = analyticsService,
        _errorTracking = errorTrackingService;

  final AnalyticsService _analytics;
  final ErrorTrackingService _errorTracking;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  /// Whether the user has granted **analytics** consent.
  bool get analyticsConsentGranted => _analytics.consentGranted;

  /// Whether the user has granted **error-tracking** consent.
  bool get errorTrackingConsentGranted => _errorTracking.consentGranted;

  /// Convenience — true when at least one consent type is active.
  bool get hasAnyConsent =>
      analyticsConsentGranted || errorTrackingConsentGranted;

  // ---------------------------------------------------------------------------
  // Consent management
  // ---------------------------------------------------------------------------

  /// Grant analytics consent and notify listeners.
  Future<void> grantAnalyticsConsent() async {
    await _analytics.grantConsent();
    notifyListeners();
  }

  /// Revoke analytics consent and notify listeners.
  Future<void> revokeAnalyticsConsent() async {
    await _analytics.revokeConsent();
    notifyListeners();
  }

  /// Grant error-tracking consent and notify listeners.
  Future<void> grantErrorTrackingConsent() async {
    await _errorTracking.grantConsent();
    notifyListeners();
  }

  /// Revoke error-tracking consent and notify listeners.
  Future<void> revokeErrorTrackingConsent() async {
    await _errorTracking.revokeConsent();
    notifyListeners();
  }

  /// Accept all consent types at once.
  Future<void> acceptAll() async {
    await _analytics.grantConsent();
    await _errorTracking.grantConsent();
    notifyListeners();
  }

  /// Revoke all consent types at once.
  Future<void> revokeAll() async {
    await _analytics.revokeConsent();
    await _errorTracking.revokeConsent();
    notifyListeners();
  }

  // ---------------------------------------------------------------------------
  // Tracking pass-through
  // ---------------------------------------------------------------------------

  /// Track an analytics event (delegates to [AnalyticsService]).
  Future<void> trackEvent(
    String name, {
    Map<String, dynamic>? properties,
  }) =>
      _analytics.trackEvent(name, properties: properties);

  /// Track a screen view.
  Future<void> trackScreen(String screenName) =>
      _analytics.trackScreen(screenName);

  /// Capture an exception via Sentry.
  Future<void> captureException(
    dynamic exception, {
    dynamic stackTrace,
  }) =>
      _errorTracking.captureException(exception, stackTrace: stackTrace);
}
