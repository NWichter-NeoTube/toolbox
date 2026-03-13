/// Application configuration loaded from build-time environment variables.
///
/// Pass values via `--dart-define` flags:
/// ```bash
/// flutter run \
///   --dart-define=UMAMI_HOST=https://track.sorevo.de \
///   --dart-define=UMAMI_WEBSITE_ID=your-website-id \
///   --dart-define=GLITCHTIP_DSN=https://key@logs.example.com/1 \
///   --dart-define=FEATURE_DARK_MODE=false \
///   --dart-define=FEATURE_ONBOARDING_V2=true
/// ```
class AppConfig {
  AppConfig._();

  // ---------------------------------------------------------------------------
  // Umami (self-hosted analytics)
  // ---------------------------------------------------------------------------

  static const String umamiHost = String.fromEnvironment(
    'UMAMI_HOST',
    defaultValue: '',
  );

  static const String umamiWebsiteId = String.fromEnvironment(
    'UMAMI_WEBSITE_ID',
    defaultValue: '',
  );

  // ---------------------------------------------------------------------------
  // GlitchTip (self-hosted error tracking, Sentry-compatible)
  // ---------------------------------------------------------------------------

  static const String glitchtipDsn = String.fromEnvironment(
    'GLITCHTIP_DSN',
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

  /// Returns `true` when the required Umami env vars are present.
  static bool get isUmamiConfigured =>
      umamiHost.isNotEmpty && umamiWebsiteId.isNotEmpty;

  /// Returns `true` when the required GlitchTip env var is present.
  static bool get isGlitchTipConfigured => glitchtipDsn.isNotEmpty;
}
