/// Application configuration loaded from build-time environment variables.
///
/// Pass values via `--dart-define` flags:
/// ```bash
/// flutter run \
///   --dart-define=POSTHOG_API_KEY=phc_xxx \
///   --dart-define=POSTHOG_HOST=https://posthog.example.com \
///   --dart-define=SENTRY_DSN=https://key@sentry.example.com/4 \
///   --dart-define=UNLEASH_URL=https://unleash.example.com/api/frontend \
///   --dart-define=UNLEASH_CLIENT_KEY=your-frontend-token
/// ```
class AppConfig {
  AppConfig._();

  // ---------------------------------------------------------------------------
  // PostHog (self-hosted analytics)
  // ---------------------------------------------------------------------------

  static const String postHogApiKey = String.fromEnvironment(
    'POSTHOG_API_KEY',
    defaultValue: '',
  );

  static const String postHogHost = String.fromEnvironment(
    'POSTHOG_HOST',
    defaultValue: 'https://posthog.example.com',
  );

  // ---------------------------------------------------------------------------
  // Sentry (self-hosted error tracking)
  // ---------------------------------------------------------------------------

  static const String sentryDsn = String.fromEnvironment(
    'SENTRY_DSN',
    defaultValue: '',
  );

  // ---------------------------------------------------------------------------
  // Unleash (self-hosted feature flags)
  // ---------------------------------------------------------------------------

  static const String unleashUrl = String.fromEnvironment(
    'UNLEASH_URL',
    defaultValue: 'https://unleash.example.com/api/frontend',
  );

  static const String unleashClientKey = String.fromEnvironment(
    'UNLEASH_CLIENT_KEY',
    defaultValue: '',
  );

  // ---------------------------------------------------------------------------
  // Shared Preferences keys
  // ---------------------------------------------------------------------------

  static const String consentAnalyticsKey = 'consent_analytics';
  static const String consentErrorTrackingKey = 'consent_error_tracking';
  static const String consentShownKey = 'consent_shown';

  // ---------------------------------------------------------------------------
  // Validation helpers
  // ---------------------------------------------------------------------------

  /// Returns `true` when the required PostHog env vars are present.
  static bool get isPostHogConfigured => postHogApiKey.isNotEmpty;

  /// Returns `true` when the required Sentry env var is present.
  static bool get isSentryConfigured => sentryDsn.isNotEmpty;

  /// Returns `true` when the required Unleash env vars are present.
  static bool get isUnleashConfigured =>
      unleashUrl.isNotEmpty && unleashClientKey.isNotEmpty;
}
