import Foundation

// MARK: - Feature Flag Manager

/// ENV-based feature flag manager.
///
/// Reads feature flags from Info.plist (injected via xcconfig / build settings)
/// with a fallback to process environment variables (useful for testing).
/// All flags use the `FEATURE_` prefix convention.
///
/// Flags degrade gracefully: if a flag is not defined, `isEnabled` returns
/// `false`.
@MainActor
final class FeatureFlagManager: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isReady: Bool = true  // Always ready with ENV flags

    // MARK: - Init

    init() {}

    // MARK: - Public API

    /// Check if a feature flag is enabled via build configuration.
    ///
    /// Looks up `FEATURE_<FLAG>` in Info.plist first, then falls back to
    /// the process environment.
    func isEnabled(_ flag: String) -> Bool {
        let key = "FEATURE_\(flag.uppercased())"

        // Read from Info.plist (set via xcconfig or build settings)
        if let value = Bundle.main.infoDictionary?[key] as? String {
            return value.lowercased() == "true" || value == "1"
        }

        // Fallback to environment (useful for testing)
        if let value = ProcessInfo.processInfo.environment[key] {
            return value.lowercased() == "true" || value == "1"
        }

        return false
    }
}
