import SwiftUI

// MARK: - Toolbox App

/// SwiftUI application entry point.
///
/// Initialises GlitchTip (Sentry-compatible) for error tracking, configures
/// Umami analytics in opted-out mode, and shows the DSGVO/GDPR consent
/// banner on first launch before any tracking occurs.
@main
struct ToolboxApp: App {

    // MARK: - State Objects

    @StateObject private var analytics = AnalyticsManager()
    @StateObject private var featureFlags = FeatureFlagManager()

    @AppStorage(Config.Defaults.hasSeenConsent)
    private var hasSeenConsent = false

    // MARK: - Init

    init() {
        // GlitchTip is initialised early so crashes during startup are captured.
        // No PII is sent until the user grants error-tracking consent.
        ErrorTracker.initialize(dsn: Config.glitchtipDSN)
    }

    // MARK: - Body

    var body: some Scene {
        WindowGroup {
            ZStack {
                HomeView()

                if !hasSeenConsent {
                    ConsentView(hasSeenConsent: $hasSeenConsent)
                        .transition(.opacity)
                }
            }
            .animation(.easeInOut, value: hasSeenConsent)
            .environmentObject(analytics)
            .environmentObject(featureFlags)
        }
    }
}
