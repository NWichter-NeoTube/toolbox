import SwiftUI

// MARK: - Consent View

/// DSGVO / GDPR consent banner shown on first launch.
///
/// Presents three options:
///  - **Accept All** -- analytics + error tracking enabled.
///  - **Only Essential** -- everything disabled except crash-free operation.
///  - **Customize** -- per-category toggles.
struct ConsentView: View {

    @EnvironmentObject private var analytics: AnalyticsManager
    @Binding var hasSeenConsent: Bool

    @State private var showCustomize = false
    @State private var analyticsToggle = false
    @State private var errorTrackingToggle = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            VStack(spacing: 24) {
                headerSection
                descriptionSection

                if showCustomize {
                    customizeSection
                }

                buttonsSection
            }
            .padding(24)
            .background(.regularMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .shadow(color: .black.opacity(0.15), radius: 20, y: 10)
            .padding(.horizontal, 16)

            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black.opacity(0.4).ignoresSafeArea())
    }

    // MARK: - Sections

    private var headerSection: some View {
        VStack(spacing: 8) {
            Image(systemName: "hand.raised.fill")
                .font(.system(size: 36))
                .foregroundStyle(.blue)
                .accessibilityHidden(true)

            Text("Your Privacy Matters")
                .font(.title2.bold())
                .multilineTextAlignment(.center)
        }
    }

    private var descriptionSection: some View {
        Text(
            "We use analytics to improve the app and error tracking to fix crashes. "
            + "No data is shared with third parties. All services are self-hosted."
        )
        .font(.subheadline)
        .foregroundStyle(.secondary)
        .multilineTextAlignment(.center)
        .fixedSize(horizontal: false, vertical: true)
    }

    private var customizeSection: some View {
        VStack(spacing: 12) {
            Divider()

            Toggle(isOn: $analyticsToggle) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Analytics")
                            .font(.subheadline.weight(.medium))
                        Text("Anonymous usage data via PostHog")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } icon: {
                    Image(systemName: "chart.bar.fill")
                }
            }
            .tint(.blue)

            Toggle(isOn: $errorTrackingToggle) {
                Label {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Error Tracking")
                            .font(.subheadline.weight(.medium))
                        Text("Crash reports via Sentry")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } icon: {
                    Image(systemName: "exclamationmark.triangle.fill")
                }
            }
            .tint(.blue)

            Divider()
        }
        .transition(.opacity.combined(with: .move(edge: .top)))
    }

    private var buttonsSection: some View {
        VStack(spacing: 12) {
            // Accept All
            Button {
                acceptAll()
            } label: {
                Text("Accept All")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("consent_accept_all")

            HStack(spacing: 12) {
                // Only Essential
                Button {
                    acceptEssentialOnly()
                } label: {
                    Text("Only Essential")
                        .font(.subheadline.weight(.medium))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.bordered)
                .accessibilityIdentifier("consent_essential_only")

                // Customize
                Button {
                    withAnimation(.easeInOut(duration: 0.25)) {
                        if showCustomize {
                            applyCustomChoices()
                        } else {
                            showCustomize = true
                        }
                    }
                } label: {
                    Text(showCustomize ? "Save" : "Customize")
                        .font(.subheadline.weight(.medium))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.bordered)
                .accessibilityIdentifier("consent_customize")
            }
        }
    }

    // MARK: - Actions

    private func acceptAll() {
        applyConsent(analytics: true, errorTracking: true)
    }

    private func acceptEssentialOnly() {
        applyConsent(analytics: false, errorTracking: false)
    }

    private func applyCustomChoices() {
        applyConsent(analytics: analyticsToggle, errorTracking: errorTrackingToggle)
    }

    private func applyConsent(analytics analyticsEnabled: Bool, errorTracking: Bool) {
        let defaults = UserDefaults.standard
        defaults.set(true, forKey: Config.Defaults.hasSeenConsent)
        defaults.set(analyticsEnabled, forKey: Config.Defaults.analyticsConsent)
        defaults.set(errorTracking, forKey: Config.Defaults.errorTrackingConsent)

        if analyticsEnabled {
            analytics.grantConsent()
        } else {
            analytics.revokeConsent()
        }

        if errorTracking {
            // User context can be set later after login.
        } else {
            ErrorTracker.clearUser()
        }

        withAnimation {
            hasSeenConsent = true
        }
    }
}

// MARK: - Preview

#if DEBUG
#Preview {
    ConsentView(hasSeenConsent: .constant(false))
        .environmentObject(AnalyticsManager())
}
#endif
