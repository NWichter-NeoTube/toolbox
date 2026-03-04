# Toolbox iOS Boilerplate

Swift/SwiftUI boilerplate for the self-hosted SaaS toolbox stack. Ships with PostHog (analytics), Sentry (error tracking), and Unleash (feature flags) -- all self-hosted and DSGVO/GDPR-ready.

## Requirements

- Xcode 15+
- iOS 16+
- Swift 5.9+

## Setup

1. Copy `.env.example` to your xcconfig or `Info.plist` build settings:

   ```
   POSTHOG_API_KEY = phc_your_key
   POSTHOG_HOST = https://posthog.example.com
   SENTRY_DSN = https://key@sentry.example.com/5
   UNLEASH_URL = https://unleash.example.com/api/frontend
   UNLEASH_CLIENT_KEY = your-frontend-token
   ```

2. Reference the keys in your target's `Info.plist`:

   ```xml
   <key>POSTHOG_API_KEY</key>
   <string>$(POSTHOG_API_KEY)</string>
   <key>POSTHOG_HOST</key>
   <string>$(POSTHOG_HOST)</string>
   <key>SENTRY_DSN</key>
   <string>$(SENTRY_DSN)</string>
   <key>UNLEASH_URL</key>
   <string>$(UNLEASH_URL)</string>
   <key>UNLEASH_CLIENT_KEY</key>
   <string>$(UNLEASH_CLIENT_KEY)</string>
   ```

3. Resolve packages:

   ```bash
   swift package resolve
   ```

## Consent Flow

The app follows a strict consent-before-tracking approach:

1. On first launch a consent banner is shown (see `ConsentView`).
2. PostHog starts in **opted-out** mode -- no data is collected until the user consents.
3. Sentry initialises without PII; user context is only attached after consent.
4. Users can change their choices at any time via **Settings > Privacy**.
5. "Reset All Consent" revokes everything and re-shows the banner on next launch.

Consent state is persisted in `UserDefaults` under the `toolbox_*` keys defined in `Config.Defaults`.

## Architecture

```
Sources/
  ToolboxApp.swift              App entry point
  Core/
    Config.swift                Centralised configuration from Info.plist / xcconfig
    AnalyticsManager.swift      Consent-aware PostHog wrapper (ObservableObject)
    FeatureFlagManager.swift    Unleash wrapper (ObservableObject)
    ErrorTracker.swift          Sentry wrapper (static)
  Providers/
    ConsentView.swift           GDPR consent banner
    HomeView.swift              Main screen with flag demos and diagnostics
    SettingsView.swift          Privacy toggles and consent reset
Tests/
  AnalyticsManagerTests.swift   Consent, persistence, and tracking guard tests
```

## Testing

```bash
swift test
```

Tests use an isolated `UserDefaults` suite so they never interfere with the app's real preferences.

## Connection to the Toolbox

This boilerplate is designed to work with the rest of the self-hosted toolbox stack:

- **PostHog** instance at `POSTHOG_HOST` for product analytics.
- **Sentry** instance at the host encoded in `SENTRY_DSN` for error tracking.
- **Unleash** frontend API at `UNLEASH_URL` for feature flags.

All three services run on your own infrastructure -- no data leaves your environment.
