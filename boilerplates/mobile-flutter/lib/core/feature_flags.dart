/// Feature flags via environment variables / compile-time constants.
///
/// Flags are defined at build time using `--dart-define` and cannot change at
/// runtime. This keeps the implementation simple and avoids the need for a
/// remote feature-flag server.
///
/// Usage:
/// ```bash
/// flutter run \
///   --dart-define=FEATURE_DARK_MODE=true \
///   --dart-define=FEATURE_ONBOARDING_V2=false
/// ```
class FeatureFlagService {
  static final FeatureFlagService _instance = FeatureFlagService._internal();
  factory FeatureFlagService() => _instance;
  FeatureFlagService._internal();

  // Define flags with defaults. Override via --dart-define or .env
  static const _flags = {
    'dark_mode': String.fromEnvironment('FEATURE_DARK_MODE', defaultValue: 'false'),
    'onboarding_v2': String.fromEnvironment('FEATURE_ONBOARDING_V2', defaultValue: 'true'),
  };

  /// Check whether [flag] is enabled. Returns `false` for unknown flags.
  bool isEnabled(String flag) {
    final value = _flags[flag.toLowerCase()] ?? 'false';
    return value == 'true' || value == '1';
  }

  /// Return all flags and their current boolean values.
  Map<String, bool> getAllFlags() {
    return _flags.map(
      (key, value) => MapEntry(key, value == 'true' || value == '1'),
    );
  }
}
