import 'package:posthog_flutter/posthog_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';

/// Consent-aware analytics service wrapping self-hosted PostHog.
///
/// Operates in cookieless mode by default (no persistence). Full tracking is
/// enabled only after the user explicitly grants consent, satisfying
/// DSGVO/GDPR requirements.
class AnalyticsService {
  AnalyticsService();

  bool _initialized = false;
  bool _consentGranted = false;

  /// Whether the PostHog SDK has been initialized.
  bool get isInitialized => _initialized;

  /// Whether the user has granted analytics consent.
  bool get consentGranted => _consentGranted;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  /// Initialize PostHog in cookieless / anonymous mode.
  ///
  /// No personal data is persisted until [grantConsent] is called.
  Future<void> init() async {
    if (!AppConfig.isPostHogConfigured) {
      return;
    }

    try {
      final posthog = Posthog();
      // PostHog Flutter SDK is configured via AndroidManifest.xml / Info.plist
      // or via the Posthog().setup() call. Here we ensure opt-out by default.
      await posthog.disable();

      _initialized = true;

      // Restore previous consent state.
      final prefs = await SharedPreferences.getInstance();
      _consentGranted =
          prefs.getBool(AppConfig.consentAnalyticsKey) ?? false;

      if (_consentGranted) {
        await posthog.enable();
      }
    } catch (_) {
      // Graceful degradation — analytics failure must never crash the app.
      _initialized = false;
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

  /// Grant analytics consent — enables full PostHog tracking and persists the
  /// preference to SharedPreferences.
  Future<void> grantConsent() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConfig.consentAnalyticsKey, true);
    _consentGranted = true;

    if (_initialized) {
      try {
        final posthog = Posthog();
        await posthog.enable();
      } catch (_) {
        // Swallow — non-critical.
      }
    }
  }

  /// Revoke analytics consent — disables tracking, clears stored data and
  /// resets to anonymous mode.
  Future<void> revokeConsent() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(AppConfig.consentAnalyticsKey, false);
    _consentGranted = false;

    if (_initialized) {
      try {
        final posthog = Posthog();
        await posthog.disable();
        await posthog.reset();
      } catch (_) {
        // Swallow — non-critical.
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Tracking helpers
  // ---------------------------------------------------------------------------

  /// Track a named event. Events are silently dropped when the SDK is not
  /// initialized or consent has not been granted.
  Future<void> trackEvent(
    String name, {
    Map<String, dynamic>? properties,
  }) async {
    if (!_initialized || !_consentGranted) return;

    try {
      final posthog = Posthog();
      await posthog.capture(
        eventName: name,
        properties: properties,
      );
    } catch (_) {
      // Swallow — analytics must never disrupt UX.
    }
  }

  /// Identify a user. Only fires when consent has been granted.
  Future<void> identifyUser(
    String userId, {
    Map<String, dynamic>? properties,
  }) async {
    if (!_initialized || !_consentGranted) return;

    try {
      final posthog = Posthog();
      await posthog.identify(
        userId: userId,
        userProperties: properties,
      );
    } catch (_) {
      // Swallow.
    }
  }

  /// Track a screen view.
  Future<void> trackScreen(String screenName) async {
    if (!_initialized || !_consentGranted) return;

    try {
      final posthog = Posthog();
      await posthog.screen(
        screenName: screenName,
      );
    } catch (_) {
      // Swallow.
    }
  }
}
