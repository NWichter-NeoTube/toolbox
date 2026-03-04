import SwiftUI

// MARK: - Home View

/// Main screen with feature-flag examples and diagnostic buttons.
struct HomeView: View {

    @EnvironmentObject private var analytics: AnalyticsManager
    @EnvironmentObject private var featureFlags: FeatureFlagManager

    @State private var showErrorAlert = false

    var body: some View {
        NavigationStack {
            List {
                featureFlagSection
                diagnosticsSection
                navigationSection
            }
            .navigationTitle("Toolbox")
            .onAppear {
                analytics.trackScreen(name: "Home")
            }
            .alert("Test Error Sent", isPresented: $showErrorAlert) {
                Button("OK", role: .cancel) {}
            } message: {
                Text("A test error has been sent to Sentry.")
            }
        }
    }

    // MARK: - Sections

    private var featureFlagSection: some View {
        Section {
            featureFlagStatusRow

            featureFlagRow("new_onboarding", label: "New Onboarding Flow")
            featureFlagRow("premium_features", label: "Premium Features")
            featureFlagRow("dark_mode_v2", label: "Dark Mode v2")
        } header: {
            Text("Feature Flags")
        } footer: {
            Text("Flags are fetched from your self-hosted Unleash instance.")
        }
    }

    private var diagnosticsSection: some View {
        Section("Diagnostics") {
            Button {
                analytics.trackEvent(
                    name: "test_event",
                    properties: ["source": "home_screen", "timestamp": ISO8601DateFormatter().string(from: .now)]
                )
            } label: {
                Label("Send Test Event", systemImage: "paperplane")
            }
            .accessibilityIdentifier("send_test_event")

            Button(role: .destructive) {
                triggerTestError()
            } label: {
                Label("Trigger Test Error", systemImage: "exclamationmark.octagon")
            }
            .accessibilityIdentifier("trigger_test_error")
        }
    }

    private var navigationSection: some View {
        Section {
            NavigationLink {
                SettingsView()
            } label: {
                Label("Settings", systemImage: "gear")
            }
        }
    }

    // MARK: - Components

    private var featureFlagStatusRow: some View {
        HStack {
            Text("Unleash Status")
                .font(.subheadline)
            Spacer()
            if featureFlags.isReady {
                Label("Connected", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .font(.caption)
            } else {
                Label("Connecting...", systemImage: "arrow.triangle.2.circlepath")
                    .foregroundStyle(.orange)
                    .font(.caption)
            }
        }
    }

    private func featureFlagRow(_ flag: String, label: String) -> some View {
        HStack {
            Text(label)
            Spacer()
            Text(featureFlags.isEnabled(flag) ? "ON" : "OFF")
                .font(.caption.weight(.semibold))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    featureFlags.isEnabled(flag)
                        ? Color.green.opacity(0.15)
                        : Color.secondary.opacity(0.1)
                )
                .foregroundStyle(featureFlags.isEnabled(flag) ? .green : .secondary)
                .clipShape(Capsule())
        }
    }

    // MARK: - Actions

    private func triggerTestError() {
        let error = NSError(
            domain: "com.toolbox.test",
            code: 42,
            userInfo: [NSLocalizedDescriptionKey: "Test error triggered from HomeView"]
        )
        ErrorTracker.capture(error)
        ErrorTracker.addBreadcrumb(message: "User triggered test error from HomeView")
        showErrorAlert = true
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    HomeView()
        .environmentObject(AnalyticsManager())
        .environmentObject(FeatureFlagManager())
}
#endif
