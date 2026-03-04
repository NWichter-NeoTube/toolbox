# Toolbox Mobile (Flutter)

Self-hosted SaaS toolbox mobile app boilerplate with DSGVO/GDPR-compliant consent flow.

## Stack

| Service         | Purpose          | Self-hosted |
|-----------------|------------------|-------------|
| PostHog         | Analytics        | Yes         |
| Sentry          | Error tracking   | Yes         |
| Unleash         | Feature flags    | Yes         |

All telemetry data stays on your infrastructure. No third-party SaaS receives user data.

## Setup

### 1. Environment variables

Copy `.env.example` and fill in your values. Variables are passed at build time via `--dart-define`:

```bash
flutter run \
  --dart-define=POSTHOG_API_KEY=phc_xxx \
  --dart-define=POSTHOG_HOST=https://posthog.example.com \
  --dart-define=SENTRY_DSN=https://key@sentry.example.com/4 \
  --dart-define=UNLEASH_URL=https://unleash.example.com/api/frontend \
  --dart-define=UNLEASH_CLIENT_KEY=your-frontend-token
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

1. PostHog starts in opt-out (cookieless) mode -- no events are sent.
2. Sentry initializes with `sendDefaultPii: false` -- no user context is attached.
3. When the user grants consent, PostHog is enabled and Sentry receives user scope.
4. Revoking consent disables PostHog, resets the anonymous ID, and clears Sentry user scope.

## Architecture

```
lib/
  main.dart                    -- App entry point, Sentry wrapper, provider setup
  core/
    config.dart                -- Build-time configuration via --dart-define
    analytics.dart             -- Consent-aware PostHog wrapper
    feature_flags.dart         -- Unleash client wrapper with graceful fallback
    error_tracking.dart        -- Consent-aware Sentry wrapper
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

- **PostHog** instance shared with web apps for unified analytics.
- **Sentry** instance shared for cross-platform error tracking.
- **Unleash** instance shared for consistent feature flag rollouts across platforms.

Configure each service URL to point to your toolbox deployment.
