import Foundation
import Combine
import UnleashProxyClientSwift

// MARK: - Feature Flag Manager

/// ObservableObject wrapper around the Unleash frontend API.
///
/// Connects to a self-hosted Unleash instance and keeps flag state
/// synchronised.  All lookups degrade gracefully: if the SDK is not
/// ready yet or the connection fails, `isEnabled` returns `false` and
/// `getVariant` returns `nil`.
final class FeatureFlagManager: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isReady: Bool = false

    // MARK: - Private

    private var unleash: UnleashClientProtocol?
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Init

    init() {
        connect()
    }

    // MARK: - Connection

    private func connect() {
        guard !Config.unleashURL.isEmpty, !Config.unleashClientKey.isEmpty else {
            print("[FeatureFlagManager] Unleash URL or client key missing -- skipping.")
            return
        }

        let client = UnleashProxyClientSwift.UnleashClient(
            unleashUrl: Config.unleashURL,
            clientKey: Config.unleashClientKey,
            refreshInterval: 30,
            appName: "toolbox-ios"
        )

        client.subscribe(name: "ready") { [weak self] in
            DispatchQueue.main.async {
                self?.isReady = true
            }
        }

        client.subscribe(name: "update") { [weak self] in
            DispatchQueue.main.async {
                self?.objectWillChange.send()
            }
        }

        client.subscribe(name: "error") { [weak self] in
            print("[FeatureFlagManager] Unleash connection error.")
            DispatchQueue.main.async {
                self?.isReady = false
            }
        }

        client.start()
        self.unleash = client
    }

    // MARK: - Public API

    /// Check whether a feature flag is enabled.  Returns `false` when the
    /// SDK is not ready or the flag does not exist.
    func isEnabled(_ flag: String) -> Bool {
        guard isReady else { return false }
        return unleash?.isEnabled(name: flag) ?? false
    }

    /// Retrieve the variant for a flag.  Returns `nil` when unavailable.
    func getVariant(_ flag: String) -> Variant? {
        guard isReady else { return nil }
        return unleash?.getVariant(name: flag)
    }
}
