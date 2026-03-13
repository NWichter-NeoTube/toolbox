import Foundation

// MARK: - App Configuration

/// Central configuration loaded from Info.plist / xcconfig build settings.
/// All keys are injected at build time so no secrets live in source control.
enum Config {

    // MARK: - Umami (Analytics)

    static let umamiHost: String = {
        guard let host = Bundle.main.infoDictionary?["UMAMI_HOST"] as? String,
              !host.isEmpty, !host.hasPrefix("$(") else {
            assertionFailure("UMAMI_HOST not set in Info.plist / xcconfig")
            return "https://track.sorevo.de"
        }
        return host
    }()

    static let umamiWebsiteId: String = {
        guard let id = Bundle.main.infoDictionary?["UMAMI_WEBSITE_ID"] as? String,
              !id.isEmpty, !id.hasPrefix("$(") else {
            assertionFailure("UMAMI_WEBSITE_ID not set in Info.plist / xcconfig")
            return ""
        }
        return id
    }()

    // MARK: - GlitchTip (Error Tracking, Sentry-compatible)

    static let glitchtipDSN: String = {
        guard let dsn = Bundle.main.infoDictionary?["GLITCHTIP_DSN"] as? String,
              !dsn.isEmpty, !dsn.hasPrefix("$(") else {
            assertionFailure("GLITCHTIP_DSN not set in Info.plist / xcconfig")
            return ""
        }
        return dsn
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
