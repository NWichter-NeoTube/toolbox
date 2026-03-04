import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:toolbox_mobile/core/analytics.dart';
import 'package:toolbox_mobile/core/error_tracking.dart';
import 'package:toolbox_mobile/core/feature_flags.dart';
import 'package:toolbox_mobile/main.dart';
import 'package:toolbox_mobile/providers/analytics_provider.dart';
import 'package:toolbox_mobile/providers/feature_flag_provider.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('App Integration Tests', () {
    late AnalyticsService analyticsService;
    late ErrorTrackingService errorTrackingService;
    late FeatureFlagService featureFlagService;

    setUp(() {
      SharedPreferences.setMockInitialValues({});
      analyticsService = AnalyticsService();
      errorTrackingService = ErrorTrackingService();
      featureFlagService = FeatureFlagService();
    });

    /// Helper that builds the app wrapped in providers for testing.
    Widget buildTestApp() {
      return MultiProvider(
        providers: [
          ChangeNotifierProvider(
            create: (_) => AnalyticsProvider(
              analyticsService: analyticsService,
              errorTrackingService: errorTrackingService,
            ),
          ),
          ChangeNotifierProvider(
            create: (_) => FeatureFlagProvider(
              featureFlagService: featureFlagService,
            ),
          ),
        ],
        child: const ToolboxApp(),
      );
    }

    testWidgets('app launches and consent dialog appears on first run',
        (tester) async {
      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // The consent screen should be visible.
      expect(find.text('Your Privacy Matters'), findsOneWidget);
      expect(find.text('Accept All'), findsOneWidget);
      expect(find.text('Only Essential'), findsOneWidget);
      expect(find.text('Customize'), findsOneWidget);
    });

    testWidgets('accept all consent navigates to home screen', (tester) async {
      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // Tap "Accept All".
      await tester.tap(find.text('Accept All'));
      await tester.pumpAndSettle();

      // Home screen should now be visible.
      expect(find.text('Toolbox'), findsOneWidget);
      expect(find.text('Feature Flags'), findsOneWidget);
      expect(find.text('Analytics'), findsOneWidget);
      expect(find.text('Error Tracking'), findsOneWidget);
    });

    testWidgets('only essential consent navigates to home screen',
        (tester) async {
      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // Tap "Only Essential".
      await tester.tap(find.text('Only Essential'));
      await tester.pumpAndSettle();

      // Home screen should be visible.
      expect(find.text('Toolbox'), findsOneWidget);
    });

    testWidgets('customize flow works', (tester) async {
      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // Tap "Customize".
      await tester.tap(find.text('Customize'));
      await tester.pumpAndSettle();

      // Toggle switches should be visible.
      expect(find.text('Analytics'), findsOneWidget);
      expect(find.text('Error Tracking'), findsOneWidget);
      expect(find.text('Save Preferences'), findsOneWidget);

      // Enable analytics toggle.
      final analyticsSwitch = find.byType(Switch).first;
      await tester.tap(analyticsSwitch);
      await tester.pumpAndSettle();

      // Save preferences.
      await tester.tap(find.text('Save Preferences'));
      await tester.pumpAndSettle();

      // Home screen should appear.
      expect(find.text('Toolbox'), findsOneWidget);
    });

    testWidgets('consent dialog does not appear after consent was given',
        (tester) async {
      // Pre-set consent as already shown.
      SharedPreferences.setMockInitialValues({
        'consent_shown': true,
        'consent_analytics': true,
        'consent_error_tracking': true,
      });

      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // Should go directly to home screen.
      expect(find.text('Your Privacy Matters'), findsNothing);
      expect(find.text('Toolbox'), findsOneWidget);
    });

    testWidgets('settings screen is accessible from home', (tester) async {
      SharedPreferences.setMockInitialValues({
        'consent_shown': true,
      });

      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // Tap settings icon.
      await tester.tap(find.byIcon(Icons.settings));
      await tester.pumpAndSettle();

      // Settings screen should be visible.
      expect(find.text('Settings'), findsOneWidget);
      expect(find.text('Privacy & Consent'), findsOneWidget);
    });
  });
}
