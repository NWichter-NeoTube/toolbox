import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/analytics_provider.dart';

/// Full-screen consent prompt shown on first launch.
///
/// The user can:
/// - **Accept All** — enable both analytics and error tracking.
/// - **Only Essential** — reject all optional tracking.
/// - **Customize** — toggle individual categories.
///
/// Consent choices are persisted via [AnalyticsProvider] into SharedPreferences
/// and can be modified later from the settings screen.
class ConsentScreen extends StatefulWidget {
  const ConsentScreen({super.key, required this.onComplete});

  /// Called after the user has made a consent choice and the dialog should
  /// close.
  final VoidCallback onComplete;

  @override
  State<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<ConsentScreen> {
  bool _showCustomize = false;
  bool _analyticsEnabled = false;
  bool _errorTrackingEnabled = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),

              // ---------------------------------------------------------------
              // Header
              // ---------------------------------------------------------------
              Icon(
                Icons.privacy_tip_outlined,
                size: 64,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 24),
              Text(
                'Your Privacy Matters',
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Text(
                'We use self-hosted services for analytics and error '
                'tracking. Your data never leaves our infrastructure. You '
                'can change these settings at any time.',
                style: theme.textTheme.bodyLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),

              // ---------------------------------------------------------------
              // Customize toggles (conditionally visible)
              // ---------------------------------------------------------------
              if (_showCustomize) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Column(
                      children: [
                        SwitchListTile(
                          title: const Text('Analytics'),
                          subtitle: const Text(
                            'Anonymous usage data via PostHog',
                          ),
                          value: _analyticsEnabled,
                          onChanged: (v) =>
                              setState(() => _analyticsEnabled = v),
                        ),
                        const Divider(height: 1),
                        SwitchListTile(
                          title: const Text('Error Tracking'),
                          subtitle: const Text(
                            'Crash reports via Sentry',
                          ),
                          value: _errorTrackingEnabled,
                          onChanged: (v) =>
                              setState(() => _errorTrackingEnabled = v),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => _saveCustom(context),
                  child: const Text('Save Preferences'),
                ),
                const SizedBox(height: 8),
              ],

              // ---------------------------------------------------------------
              // Primary actions
              // ---------------------------------------------------------------
              if (!_showCustomize) ...[
                FilledButton(
                  onPressed: () => _acceptAll(context),
                  child: const Text('Accept All'),
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () => _onlyEssential(context),
                  child: const Text('Only Essential'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => setState(() => _showCustomize = true),
                  child: const Text('Customize'),
                ),
              ],

              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  Future<void> _acceptAll(BuildContext context) async {
    final provider = context.read<AnalyticsProvider>();
    await provider.acceptAll();
    widget.onComplete();
  }

  Future<void> _onlyEssential(BuildContext context) async {
    final provider = context.read<AnalyticsProvider>();
    await provider.revokeAll();
    widget.onComplete();
  }

  Future<void> _saveCustom(BuildContext context) async {
    final provider = context.read<AnalyticsProvider>();

    if (_analyticsEnabled) {
      await provider.grantAnalyticsConsent();
    } else {
      await provider.revokeAnalyticsConsent();
    }

    if (_errorTrackingEnabled) {
      await provider.grantErrorTrackingConsent();
    } else {
      await provider.revokeErrorTrackingConsent();
    }

    widget.onComplete();
  }
}
