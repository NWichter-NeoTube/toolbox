import 'package:flutter/foundation.dart';

import '../core/feature_flags.dart';

/// [ChangeNotifier] provider that wraps [FeatureFlagService] and provides a
/// reactive interface for the widget tree.
///
/// Since feature flags are compile-time constants (ENV-based), they do not
/// change at runtime. This provider exists for consistency with the provider
/// pattern used throughout the app.
class FeatureFlagProvider extends ChangeNotifier {
  FeatureFlagProvider({required FeatureFlagService featureFlagService})
      : _featureFlags = featureFlagService;

  final FeatureFlagService _featureFlags;

  // ---------------------------------------------------------------------------
  // Flag evaluation
  // ---------------------------------------------------------------------------

  /// Check whether [flagName] is enabled.
  bool isEnabled(String flagName) => _featureFlags.isEnabled(flagName);

  /// Return all flags and their current boolean values.
  Map<String, bool> getAllFlags() => _featureFlags.getAllFlags();
}
