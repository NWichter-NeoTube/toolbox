import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/analytics_provider.dart';
import '../providers/feature_flag_provider.dart';
import 'settings_screen.dart';

/// Main home screen demonstrating feature flags, analytics events, and
/// GlitchTip error reporting.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final analytics = context.watch<AnalyticsProvider>();
    final flags = context.watch<FeatureFlagProvider>();

    // Track screen view.
    analytics.trackScreen('home');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Toolbox'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Settings',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute<void>(
                builder: (_) => const SettingsScreen(),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // -----------------------------------------------------------------
          // Feature flags section
          // -----------------------------------------------------------------
          Text(
            'Feature Flags',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _FlagRow(
                    label: 'dark_mode',
                    enabled: flags.isEnabled('dark_mode'),
                  ),
                  const Divider(),
                  _FlagRow(
                    label: 'onboarding_v2',
                    enabled: flags.isEnabled('onboarding_v2'),
                  ),
                  const Divider(),
                  Text(
                    'ENV-based feature flags (compile-time)',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: Colors.grey,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // -----------------------------------------------------------------
          // Analytics test
          // -----------------------------------------------------------------
          Text(
            'Analytics',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    analytics.analyticsConsentGranted
                        ? 'Consent: granted'
                        : 'Consent: not granted',
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    icon: const Icon(Icons.send),
                    label: const Text('Send Test Event'),
                    onPressed: () {
                      analytics.trackEvent(
                        'test_event',
                        properties: {'source': 'home_screen'},
                      );
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Test event sent (if consent granted)'),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // -----------------------------------------------------------------
          // GlitchTip error tracking test
          // -----------------------------------------------------------------
          Text(
            'Error Tracking',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    analytics.errorTrackingConsentGranted
                        ? 'Consent: granted'
                        : 'Consent: not granted',
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    icon: const Icon(Icons.bug_report),
                    label: const Text('Send Test Error'),
                    onPressed: () {
                      try {
                        throw Exception(
                            'Test GlitchTip exception from Toolbox');
                      } catch (e, st) {
                        analytics.captureException(e, stackTrace: st);
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Test exception captured'),
                          ),
                        );
                      }
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Small helper widget that displays a feature flag and its state.
class _FlagRow extends StatelessWidget {
  const _FlagRow({required this.label, required this.enabled});

  final String label;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(
          enabled ? Icons.check_circle : Icons.cancel,
          color: enabled ? Colors.green : Colors.grey,
          size: 20,
        ),
        const SizedBox(width: 8),
        Text(label),
        const Spacer(),
        Text(
          enabled ? 'ON' : 'OFF',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: enabled ? Colors.green : Colors.grey,
          ),
        ),
      ],
    );
  }
}
