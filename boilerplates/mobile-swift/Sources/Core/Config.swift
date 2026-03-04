import Foundation

// MARK: - App Configuration

/// Central configuration loaded from Info.plist / xcconfig build settings.
/// All keys are injected at build time so no secrets live in source control.
enum Config {

    // MARK: - PostHog (Analytics)

    static let postHogAPIKey: String = {
        guard let key = Bundle.main.infoDictionary?["POSTHOG_API_KEY"] as? String,
              !key.isEmpty, !key.hasPrefix("$(") else {
            assertionFailure("POSTHOG_API_KEY not set in Info.plist / xcconfig")
            return ""
        }
        return key
    }()

    static let postHogHost: String = {
        guard let host = Bundle.main.infoDictionary?["POSTHOG_HOST"] as? String,
              !host.isEmpty, !host.hasPrefix("$(") else {
            assertionFailure("POSTHOG_HOST not set in Info.plist / xcconfig")
            return "https://posthog.example.com"
        }
        return host
    }()

    // MARK: - Sentry (Error Tracking)

    static let sentryDSN: String = {
        guard let dsn = Bundle.main.infoDictionary?["SENTRY_DSN"] as? String,
              !dsn.isEmpty, !dsn.hasPrefix("$(") else {
            assertionFailure("SENTRY_DSN not set in Info.plist / xcconfig")
            return ""
        }
        return dsn
    }()

    // MARK: - Unleash (Feature Flags)

    static let unleashURL: String = {
        guard let url = Bundle.main.infoDictionary?["UNLEASH_URL"] as? String,
              !url.isEmpty, !url.hasPrefix("$(") else {
            assertionFailure("UNLEASH_URL not set in Info.plist / xcconfig")
            return "https://unleash.example.com/api/frontend"
        }
        return url
    }()

    static let unleashClientKey: String = {
        guard let key = Bundle.main.infoDictionary?["UNLEASH_CLIENT_KEY"] as? String,
              !key.isEmpty, !key.hasPrefix("$(") else {
            assertionFailure("UNLEASH_CLIENT_KEY not set in Info.plist / xcconfig")
            return ""
        }
        return key
    }()

    // MARK: - UserDefaults Keys

    enum Defaults {
        static let consentGranted = "toolbox_consent_granted"
        static let analyticsConsent = "toolbox_analytics_consent"
        static let errorTrackingConsent = "toolbox_error_tracking_consent"
        static let hasSeenConsent = "toolbox_has_seen_consent"
    }

    // MARK: - App Meta

    static let appVersion: String = {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0"
    }()

    static let buildNumber: String = {
        Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
    }()
}
