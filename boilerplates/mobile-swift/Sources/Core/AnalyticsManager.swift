import Foundation
import Combine
import PostHog

// MARK: - Analytics Manager

/// Consent-aware PostHog wrapper.
///
/// Operates in cookieless / no-persistence mode until the user explicitly
/// grants consent via the DSGVO/GDPR consent banner.  When consent is
/// revoked every local identifier is wiped and tracking stops immediately.
final class AnalyticsManager: ObservableObject {

    // MARK: - Published State

    @Published private(set) var consentGranted: Bool

    // MARK: - Private

    private let defaults: UserDefaults

    // MARK: - Init

    /// - Parameter defaults: Injectable for testing.
    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        self.consentGranted = defaults.bool(forKey: Config.Defaults.analyticsConsent)

        configurePostHog()
    }

    // MARK: - PostHog Setup

    private func configurePostHog() {
        let config = PostHogConfig(apiKey: Config.postHogAPIKey, host: Config.postHogHost)

        // DSGVO/GDPR: start opted-out; only opt-in after explicit consent.
        config.optOut = !consentGranted

        // Cookieless / minimal-persistence mode:
        config.captureApplicationLifecycleEvents = consentGranted
        config.captureScreenViews = false  // we track manually for control
        config.flushAt = 10
        config.flushIntervalSeconds = 30

        PostHogSDK.shared.setup(config)
    }

    // MARK: - Consent

    /// Grant analytics consent. Enables tracking and persists the choice.
    func grantConsent() {
        consentGranted = true
        defaults.set(true, forKey: Config.Defaults.analyticsConsent)

        PostHogSDK.shared.optIn()
    }

    /// Revoke analytics consent. Disables tracking and clears all local data.
    func revokeConsent() {
        consentGranted = false
        defaults.set(false, forKey: Config.Defaults.analyticsConsent)

        PostHogSDK.shared.optOut()
        PostHogSDK.shared.reset()
    }

    // MARK: - Tracking

    /// Track a named event with optional properties.
    func trackEvent(name: String, properties: [String: Any]? = nil) {
        guard consentGranted else { return }
        PostHogSDK.shared.capture(name, properties: properties)
    }

    /// Identify the current user (e.g. after login).
    func identifyUser(id: String, properties: [String: Any]? = nil) {
        guard consentGranted else { return }

        var userProperties = properties ?? [:]
        userProperties["app_version"] = Config.appVersion

        PostHogSDK.shared.identify(id, userProperties: userProperties)
    }

    /// Track a screen view.
    func trackScreen(name: String) {
        guard consentGranted else { return }
        PostHogSDK.shared.screen(name)
    }
}
