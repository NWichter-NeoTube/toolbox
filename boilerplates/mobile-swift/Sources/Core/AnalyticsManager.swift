import Foundation

// MARK: - Analytics Manager

/// Consent-aware Umami analytics wrapper.
///
/// Sends events via URLSession HTTP calls to the self-hosted Umami instance.
/// No tracking occurs until the user explicitly grants consent via the
/// DSGVO/GDPR consent banner. When consent is revoked, tracking stops
/// immediately.
@MainActor
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
    }

    // MARK: - Consent

    /// Grant analytics consent. Enables tracking and persists the choice.
    func grantConsent() {
        consentGranted = true
        defaults.set(true, forKey: Config.Defaults.analyticsConsent)
    }

    /// Revoke analytics consent. Disables tracking immediately.
    func revokeConsent() {
        consentGranted = false
        defaults.set(false, forKey: Config.Defaults.analyticsConsent)
    }

    // MARK: - Tracking

    /// Track a named event with optional properties.
    func trackEvent(_ name: String, data: [String: Any]? = nil) {
        guard consentGranted else { return }

        let host = Config.umamiHost
        let websiteId = Config.umamiWebsiteId
        guard !host.isEmpty, !websiteId.isEmpty else { return }
        guard let url = URL(string: "\(host)/api/send") else { return }

        var payload: [String: Any] = [
            "website": websiteId,
            "name": name,
            "url": "/",
        ]
        if let data = data {
            payload["data"] = data
        }

        let body: [String: Any] = ["payload": payload, "type": "event"]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { _, _, _ in }.resume()
    }

    /// Track a screen view.
    func trackScreen(_ name: String) {
        trackEvent("screen_view", data: ["screen": name])
    }
}
