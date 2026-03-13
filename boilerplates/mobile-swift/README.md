# Toolbox iOS Boilerplate

Swift/SwiftUI boilerplate for the self-hosted SaaS toolbox stack. Ships with Umami (analytics), GlitchTip (error tracking), and ENV-based feature flags -- all self-hosted and DSGVO/GDPR-ready.

## Requirements

- Xcode 15+
- iOS 16+
- Swift 5.9+

## Setup

1. Copy `.env.example` to your xcconfig or `Info.plist` build settings:

   ```
   UMAMI_HOST = https://track.sorevo.de
   UMAMI_WEBSITE_ID = your-website-id
   GLITCHTIP_DSN = https://key@logs.example.com/1
   FEATURE_DARK_MODE = false
   FEATURE_ONBOARDING_V2 = true
   ```

2. Reference the keys in your target's `Info.plist`:

   ```xml
   <key>UMAMI_HOST</key>
   <string>$(UMAMI_HOST)</string>
   <key>UMAMI_WEBSITE_ID</key>
   <string>$(UMAMI_WEBSITE_ID)</string>
   <key>GLITCHTIP_DSN</key>
   <string>$(GLITCHTIP_DSN)</string>
   <key>FEATURE_DARK_MODE</key>
   <string>$(FEATURE_DARK_MODE)</string>
   <key>FEATURE_ONBOARDING_V2</key>
   <string>$(FEATURE_ONBOARDING_V2)</string>
   ```

3. Resolve packages:

   ```bash
   swift package resolve
   ```

## Consent Flow

The app follows a strict consent-before-tracking approach:

1. On first launch a consent banner is shown (see `ConsentView`).
2. Umami tracking is disabled by default -- no data is collected until the user consents.
3. GlitchTip (Sentry-compatible) initialises without PII; user context is only attached after consent.
4. Users can change their choices at any time via **Settings > Privacy**.
5. "Reset All Consent" revokes everything and re-shows the banner on next launch.

Consent state is persisted in `UserDefaults` under the `toolbox_*` keys defined in `Config.Defaults`.

## Architecture

```
Sources/
  ToolboxApp.swift              App entry point
  Core/
    Config.swift                Centralised configuration from Info.plist / xcconfig
    AnalyticsManager.swift      Consent-aware Umami wrapper (ObservableObject)
    FeatureFlagManager.swift    ENV-based feature flags (ObservableObject)
    ErrorTracker.swift          GlitchTip wrapper via Sentry SDK (static)
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

- **Umami** instance at `UMAMI_HOST` for privacy-friendly analytics.
- **GlitchTip** (Sentry-compatible) instance at the host encoded in `GLITCHTIP_DSN` for error tracking.
- **ENV-based feature flags** via Info.plist / build settings for simple, dependency-free toggles.

All services run on your own infrastructure -- no data leaves your environment.
