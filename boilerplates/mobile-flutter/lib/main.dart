import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/analytics.dart';
import 'core/config.dart';
import 'core/error_tracking.dart';
import 'core/feature_flags.dart';
import 'providers/analytics_provider.dart';
import 'providers/feature_flag_provider.dart';
import 'screens/home_screen.dart';
import 'widgets/consent_dialog.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ---------------------------------------------------------------------------
  // Core services
  // ---------------------------------------------------------------------------
  final analyticsService = AnalyticsService();
  final featureFlagService = FeatureFlagService();
  final errorTrackingService = ErrorTrackingService();

  // ---------------------------------------------------------------------------
  // GlitchTip (Sentry-compatible) must wrap runApp to capture Flutter
  // framework errors.
  // ---------------------------------------------------------------------------
  await SentryFlutter.init(
    (options) {
      options.dsn = AppConfig.glitchtipDsn;
      // Point to self-hosted GlitchTip instance -- no data leaves your infra.
      options.tracesSampleRate = 1.0;
      options.environment = const String.fromEnvironment(
        'SENTRY_ENVIRONMENT',
        defaultValue: 'development',
      );
      // Disable default user context until consent is granted.
      options.sendDefaultPii = false;
    },
    appRunner: () async {
      // Mark GlitchTip as initialized in the wrapper.
      await errorTrackingService.init(dsn: AppConfig.glitchtipDsn);

      // Initialize Umami analytics (consent state restored from prefs).
      await analyticsService.init();

      runApp(
        MultiProvider(
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
        ),
      );
    },
  );
}

/// Root widget of the Toolbox mobile application.
class ToolboxApp extends StatelessWidget {
  const ToolboxApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Toolbox',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const _ConsentGate(),
    );
  }
}

/// Gate that displays the consent dialog on first launch before navigating to
/// the home screen.
class _ConsentGate extends StatefulWidget {
  const _ConsentGate();

  @override
  State<_ConsentGate> createState() => _ConsentGateState();
}

class _ConsentGateState extends State<_ConsentGate> {
  bool _loading = true;
  bool _consentShown = false;

  @override
  void initState() {
    super.initState();
    _checkConsentState();
  }

  Future<void> _checkConsentState() async {
    final prefs = await SharedPreferences.getInstance();
    final shown = prefs.getBool(AppConfig.consentShownKey) ?? false;
    setState(() {
      _consentShown = shown;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (!_consentShown) {
      // Show consent dialog before any tracking starts.
      return ConsentScreen(
        onComplete: () async {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setBool(AppConfig.consentShownKey, true);
          if (!mounted) return;
          setState(() => _consentShown = true);
        },
      );
    }

    return const HomeScreen();
  }
}
