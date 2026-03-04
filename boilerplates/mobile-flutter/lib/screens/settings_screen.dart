import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import '../providers/analytics_provider.dart';

/// Settings screen allowing the user to view and manage their consent
/// preferences at any time (DSGVO/GDPR requirement).
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final analytics = context.watch<AnalyticsProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // -----------------------------------------------------------------
          // Consent section
          // -----------------------------------------------------------------
          Text(
            'Privacy & Consent',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Analytics'),
                  subtitle: const Text(
                    'Anonymous usage data via self-hosted PostHog',
                  ),
                  value: analytics.analyticsConsentGranted,
                  onChanged: (enabled) {
                    if (enabled) {
                      analytics.grantAnalyticsConsent();
                    } else {
                      analytics.revokeAnalyticsConsent();
                    }
                  },
                ),
                const Divider(height: 1),
                SwitchListTile(
                  title: const Text('Error Tracking'),
                  subtitle: const Text(
                    'Crash reports via self-hosted Sentry',
                  ),
                  value: analytics.errorTrackingConsentGranted,
                  onChanged: (enabled) {
                    if (enabled) {
                      analytics.grantErrorTrackingConsent();
                    } else {
                      analytics.revokeErrorTrackingConsent();
                    }
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // -----------------------------------------------------------------
          // Status overview
          // -----------------------------------------------------------------
          Text(
            'Current Status',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _StatusRow(
                    label: 'Analytics consent',
                    granted: analytics.analyticsConsentGranted,
                  ),
                  const SizedBox(height: 8),
                  _StatusRow(
                    label: 'Error tracking consent',
                    granted: analytics.errorTrackingConsentGranted,
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // -----------------------------------------------------------------
          // Reset
          // -----------------------------------------------------------------
          OutlinedButton.icon(
            icon: const Icon(Icons.restart_alt),
            label: const Text('Reset All Consent'),
            style: OutlinedButton.styleFrom(
              foregroundColor: theme.colorScheme.error,
            ),
            onPressed: () => _confirmReset(context),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Reset confirmation dialog
  // ---------------------------------------------------------------------------

  Future<void> _confirmReset(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reset Consent'),
        content: const Text(
          'This will revoke all consent, disable tracking, and clear '
          'stored preferences. The consent dialog will appear again on '
          'next launch.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Reset'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final provider = context.read<AnalyticsProvider>();
      await provider.revokeAll();

      // Clear the "consent shown" flag so the dialog reappears.
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(AppConfig.consentShownKey, false);

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Consent reset. Restart the app to see the consent dialog.',
            ),
          ),
        );
      }
    }
  }
}

/// Small status indicator for a consent category.
class _StatusRow extends StatelessWidget {
  const _StatusRow({required this.label, required this.granted});

  final String label;
  final bool granted;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(
          granted ? Icons.check_circle : Icons.cancel,
          size: 18,
          color: granted ? Colors.green : Colors.grey,
        ),
        const SizedBox(width: 8),
        Text(label),
        const Spacer(),
        Text(
          granted ? 'Granted' : 'Denied',
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: granted ? Colors.green : Colors.grey,
          ),
        ),
      ],
    );
  }
}
