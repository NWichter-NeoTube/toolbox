import 'package:flutter/foundation.dart';

import '../core/feature_flags.dart';

/// [ChangeNotifier] provider that wraps [FeatureFlagService] and provides a
/// reactive interface for the widget tree.
///
/// Listens to Unleash update events and notifies listeners so that widgets
/// using `context.watch<FeatureFlagProvider>()` are automatically rebuilt when
/// flag state changes.
class FeatureFlagProvider extends ChangeNotifier {
  FeatureFlagProvider({required FeatureFlagService featureFlagService})
      : _featureFlags = featureFlagService {
    // Subscribe to remote flag updates from the Unleash polling loop.
    _featureFlags.onUpdate(_onFlagsUpdated);
  }

  final FeatureFlagService _featureFlags;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  /// Whether the Unleash client has been initialized.
  bool get isInitialized => _featureFlags.isInitialized;

  // ---------------------------------------------------------------------------
  // Flag evaluation
  // ---------------------------------------------------------------------------

  /// Reactive check — widgets that `watch` this provider are rebuilt when any
  /// flag changes.
  bool isEnabled(String flagName) => _featureFlags.isEnabled(flagName);

  /// Get the variant payload for a flag.
  dynamic getVariant(String flagName) => _featureFlags.getVariant(flagName);

  // ---------------------------------------------------------------------------
  // Internal
  // ---------------------------------------------------------------------------

  void _onFlagsUpdated() {
    notifyListeners();
  }

  @override
  void dispose() {
    _featureFlags.dispose();
    super.dispose();
  }
}
