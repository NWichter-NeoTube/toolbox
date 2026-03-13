import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:toolbox_mobile/core/analytics.dart';
import 'package:toolbox_mobile/core/config.dart';

void main() {
  group('AnalyticsService', () {
    late AnalyticsService service;

    setUp(() {
      // Use in-memory SharedPreferences for tests.
      SharedPreferences.setMockInitialValues({});
      service = AnalyticsService();
    });

    test('starts with consent not granted', () {
      expect(service.consentGranted, isFalse);
    });

    test('hasConsent returns false when no preference stored', () async {
      final result = await service.hasConsent();
      expect(result, isFalse);
    });

    test('grantConsent persists to SharedPreferences', () async {
      await service.grantConsent();

      expect(service.consentGranted, isTrue);

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getBool(AppConfig.consentAnalyticsKey), isTrue);
    });

    test('revokeConsent clears SharedPreferences', () async {
      // First grant, then revoke.
      await service.grantConsent();
      expect(service.consentGranted, isTrue);

      await service.revokeConsent();
      expect(service.consentGranted, isFalse);

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getBool(AppConfig.consentAnalyticsKey), isFalse);
    });

    test('hasConsent reflects stored value', () async {
      SharedPreferences.setMockInitialValues({
        AppConfig.consentAnalyticsKey: true,
      });

      final result = await service.hasConsent();
      expect(result, isTrue);
    });

    test('trackEvent does nothing when consent not granted', () async {
      // Should complete without error even though Umami is not configured.
      await service.trackEvent('test_event');
    });

    test('trackEvent does nothing when consent not granted with properties',
        () async {
      await service.trackEvent('test_event', properties: {'key': 'value'});
      // No exception means pass.
    });

    test('trackScreen does nothing when consent not granted', () async {
      await service.trackScreen('test_screen');
    });

    test('consent grant/revoke cycle works correctly', () async {
      // Grant.
      await service.grantConsent();
      expect(service.consentGranted, isTrue);
      expect(await service.hasConsent(), isTrue);

      // Revoke.
      await service.revokeConsent();
      expect(service.consentGranted, isFalse);
      expect(await service.hasConsent(), isFalse);

      // Grant again.
      await service.grantConsent();
      expect(service.consentGranted, isTrue);
      expect(await service.hasConsent(), isTrue);
    });
  });
}
