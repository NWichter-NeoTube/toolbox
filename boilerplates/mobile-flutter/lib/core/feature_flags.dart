import 'package:unleash_proxy_client_flutter/unleash_proxy_client_flutter.dart';

import 'config.dart';

/// Wrapper around the Unleash frontend (proxy) client for self-hosted feature
/// flag evaluation.
///
/// Provides graceful fallback behaviour when the Unleash server is unreachable
/// or not configured.
class FeatureFlagService {
  FeatureFlagService();

  UnleashClient? _client;
  bool _initialized = false;

  /// Whether the Unleash client has successfully connected.
  bool get isInitialized => _initialized;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  /// Connect to the self-hosted Unleash frontend API.
  ///
  /// If [AppConfig.isUnleashConfigured] is `false` or the connection fails, the
  /// service degrades silently — all flags default to disabled.
  Future<void> init() async {
    if (!AppConfig.isUnleashConfigured) {
      return;
    }

    try {
      _client = UnleashClient(
        url: Uri.parse(AppConfig.unleashUrl),
        clientKey: AppConfig.unleashClientKey,
        appName: 'toolbox-mobile',
      );

      await _client!.start();
      _initialized = true;
    } catch (_) {
      // Graceful degradation — treat all flags as disabled.
      _client = null;
      _initialized = false;
    }
  }

  /// Disconnect from the Unleash server and release resources.
  void dispose() {
    _client?.close();
    _client = null;
    _initialized = false;
  }

  // ---------------------------------------------------------------------------
  // Flag evaluation
  // ---------------------------------------------------------------------------

  /// Check whether [flagName] is enabled. Returns `false` when the client is
  /// unavailable.
  bool isEnabled(String flagName) {
    if (!_initialized || _client == null) return false;

    try {
      return _client!.isEnabled(flagName);
    } catch (_) {
      return false;
    }
  }

  /// Get the variant for [flagName]. Returns `null` when the client is
  /// unavailable or no variant is assigned.
  Variant? getVariant(String flagName) {
    if (!_initialized || _client == null) return null;

    try {
      final variant = _client!.getVariant(flagName);
      // Unleash returns a disabled variant when no match — treat as null.
      if (!variant.enabled) return null;
      return variant;
    } catch (_) {
      return null;
    }
  }

  /// Register a listener that fires whenever flag state changes (e.g. after a
  /// poll refresh).
  void onUpdate(void Function() callback) {
    _client?.on('update', data: null, callback: (_) => callback());
  }
}
