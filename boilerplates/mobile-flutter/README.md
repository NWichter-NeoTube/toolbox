# Toolbox Mobile (Flutter)

Self-hosted SaaS toolbox mobile app boilerplate with DSGVO/GDPR-compliant consent flow.

## Stack

| Service         | Purpose          | Self-hosted |
|-----------------|------------------|-------------|
| Umami           | Analytics        | Yes         |
| GlitchTip       | Error tracking   | Yes         |
| ENV flags       | Feature flags    | N/A         |

All telemetry data stays on your infrastructure. No third-party SaaS receives user data.

## Setup

### 1. Environment variables

Copy `.env.example` and fill in your values. Variables are passed at build time via `--dart-define`:

```bash
flutter run \
  --dart-define=UMAMI_HOST=https://track.sorevo.de \
  --dart-define=UMAMI_WEBSITE_ID=your-website-id \
  --dart-define=GLITCHTIP_DSN=https://key@logs.example.com/1 \
  --dart-define=FEATURE_DARK_MODE=false \
  --dart-define=FEATURE_ONBOARDING_V2=true
```

### 2. Install dependencies

```bash
flutter pub get
```

### 3. Run

```bash
flutter run
```

## Consent Flow (DSGVO/GDPR)

On first launch the app displays a full-screen consent dialog with three options:

- **Accept All** -- enables analytics and error tracking.
- **Only Essential** -- no optional tracking is enabled.
- **Customize** -- granular toggles for analytics and error tracking.

Consent state is persisted in `SharedPreferences` and can be changed at any time from **Settings > Privacy & Consent**. A **Reset Consent** button clears all preferences and re-shows the consent dialog on next launch.

### How it works

1. Umami analytics are disabled until consent is granted -- no events are sent.
2. GlitchTip (Sentry-compatible) initializes with `sendDefaultPii: false` -- no user context is attached.
3. When the user grants consent, Umami events are enabled and GlitchTip receives user scope.
4. Revoking consent stops Umami events and clears GlitchTip user scope.

## Architecture

```
lib/
  main.dart                    -- App entry point, GlitchTip wrapper, provider setup
  core/
    config.dart                -- Build-time configuration via --dart-define
    analytics.dart             -- Consent-aware Umami HTTP API wrapper
    feature_flags.dart         -- ENV-based feature flags (compile-time)
    error_tracking.dart        -- Consent-aware GlitchTip (Sentry-compatible) wrapper
  providers/
    analytics_provider.dart    -- ChangeNotifier for consent state
    feature_flag_provider.dart -- ChangeNotifier for feature flags
  widgets/
    consent_dialog.dart        -- First-launch consent screen
  screens/
    home_screen.dart           -- Demo screen with flag/event/error test buttons
    settings_screen.dart       -- Consent management UI
```

## Testing

### Unit tests

```bash
flutter test
```

### Integration tests

```bash
flutter test integration_test/
```

## Connection to Toolbox

This mobile app connects to the same self-hosted infrastructure as the rest of the toolbox:

- **Umami** instance shared with web apps for unified analytics.
- **GlitchTip** instance shared for cross-platform error tracking (Sentry-compatible SDK).
- **Feature flags** are ENV-based (`--dart-define`) -- no remote server needed.

Configure each service URL to point to your toolbox deployment.
