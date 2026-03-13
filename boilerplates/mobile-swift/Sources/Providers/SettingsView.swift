import SwiftUI

// MARK: - Settings View

/// Privacy and consent settings.
struct SettingsView: View {

    @EnvironmentObject private var analytics: AnalyticsManager

    @AppStorage(Config.Defaults.analyticsConsent)
    private var analyticsConsent = false

    @AppStorage(Config.Defaults.errorTrackingConsent)
    private var errorTrackingConsent = false

    @AppStorage(Config.Defaults.hasSeenConsent)
    private var hasSeenConsent = true

    @State private var showResetConfirmation = false

    var body: some View {
        List {
            privacySection
            consentStatusSection
            dangerZone
            aboutSection
        }
        .navigationTitle("Settings")
        .onAppear {
            analytics.trackScreen("Settings")
        }
        .confirmationDialog(
            "Reset Consent",
            isPresented: $showResetConfirmation,
            titleVisibility: .visible
        ) {
            Button("Reset", role: .destructive) {
                resetConsent()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will revoke all consents and show the consent banner again on next launch.")
        }
    }

    // MARK: - Sections

    private var privacySection: some View {
        Section {
            Toggle(isOn: $analyticsConsent) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Analytics")
                        Text("Anonymous usage data via Umami")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } icon: {
                    Image(systemName: "chart.bar.fill")
                }
            }
            .tint(.blue)
            .onChange(of: analyticsConsent) { _, newValue in
                if newValue {
                    analytics.grantConsent()
                } else {
                    analytics.revokeConsent()
                }
            }

            Toggle(isOn: $errorTrackingConsent) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Error Tracking")
                        Text("Crash reports via GlitchTip")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } icon: {
                    Image(systemName: "exclamationmark.triangle.fill")
                }
            }
            .tint(.blue)
            .onChange(of: errorTrackingConsent) { _, newValue in
                if !newValue {
                    ErrorTracker.clearUser()
                }
            }
        } header: {
            Text("Privacy")
        } footer: {
            Text("All data is processed on self-hosted infrastructure. No data is shared with third parties.")
        }
    }

    private var consentStatusSection: some View {
        Section("Current Status") {
            statusRow(title: "Analytics", enabled: analyticsConsent)
            statusRow(title: "Error Tracking", enabled: errorTrackingConsent)
        }
    }

    private var dangerZone: some View {
        Section {
            Button(role: .destructive) {
                showResetConfirmation = true
            } label: {
                Label("Reset All Consent", systemImage: "arrow.counterclockwise")
            }
            .accessibilityIdentifier("reset_consent")
        } header: {
            Text("Consent")
        } footer: {
            Text("Resets all privacy choices. The consent banner will appear again on next launch.")
        }
    }

    private var aboutSection: some View {
        Section("About") {
            HStack {
                Text("Version")
                Spacer()
                Text("\(Config.appVersion) (\(Config.buildNumber))")
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Components

    private func statusRow(title: String, enabled: Bool) -> some View {
        HStack {
            Text(title)
            Spacer()
            Image(systemName: enabled ? "checkmark.circle.fill" : "xmark.circle")
                .foregroundStyle(enabled ? .green : .secondary)
        }
    }

    // MARK: - Actions

    private func resetConsent() {
        analyticsConsent = false
        errorTrackingConsent = false
        hasSeenConsent = false

        analytics.revokeConsent()
        ErrorTracker.clearUser()
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    NavigationStack {
        SettingsView()
            .environmentObject(AnalyticsManager())
    }
}
#endif
