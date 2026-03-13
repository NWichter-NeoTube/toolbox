import Foundation
import Sentry

// MARK: - Error Tracker

/// Thin, consent-aware wrapper around the Sentry SDK for GlitchTip.
///
/// GlitchTip is Sentry-compatible, so the same Sentry SDK is used.
/// Call `ErrorTracker.initialize(dsn:)` once at app launch.
/// User context is only attached when the user has granted error-tracking
/// consent (DSGVO / GDPR compliant).
enum ErrorTracker {

    // MARK: - Configuration

    /// Initialise GlitchTip (Sentry-compatible). Call this in the `App.init()`.
    static func initialize(dsn: String) {
        guard !dsn.isEmpty else {
            print("[ErrorTracker] GlitchTip DSN is empty -- skipping initialisation.")
            return
        }

        SentrySDK.start { options in
            options.dsn = dsn
            options.environment = Self.currentEnvironment
            options.releaseName = "\(Config.appVersion)+\(Config.buildNumber)"

            // Performance monitoring at a conservative sample rate.
            options.tracesSampleRate = 0.2

            // Disable default PII collection for GDPR.
            options.sendDefaultPii = false

            // Attach stack traces to all events.
            options.attachStacktrace = true

            // Enable breadcrumbs for UI events.
            options.enableAutoBreadcrumbTracking = true

            #if DEBUG
            options.debug = true
            #endif
        }
    }

    // MARK: - Error Capture

    /// Capture an `Error` as an event.
    static func capture(_ error: Error) {
        SentrySDK.capture(error: error)
    }

    /// Capture a plain message.
    static func capture(message: String, level: SentryLevel = .error) {
        let event = Sentry.Event(level: level)
        event.message = SentryMessage(formatted: message)
        SentrySDK.capture(event: event)
    }

    // MARK: - Breadcrumbs

    /// Add a manual breadcrumb for additional context.
    static func addBreadcrumb(message: String, category: String = "app") {
        let crumb = Breadcrumb(level: .info, category: category)
        crumb.message = message
        SentrySDK.addBreadcrumb(crumb)
    }

    // MARK: - User Context (Consent-Aware)

    /// Set user context on the scope.
    /// Only call this when error-tracking consent has been granted.
    static func setUser(id: String, email: String? = nil) {
        let sentryUser = Sentry.User(userId: id)
        sentryUser.email = email
        SentrySDK.setUser(sentryUser)
    }

    /// Remove all user context (call on consent revocation).
    static func clearUser() {
        SentrySDK.setUser(nil)
    }

    // MARK: - Helpers

    private static var currentEnvironment: String {
        #if DEBUG
        return "development"
        #else
        return "production"
        #endif
    }
}
