# 08 — Cookie Consent & DSGVO/GDPR Compliance

This document explains the complete cookie consent flow across all platforms, covering the full lifecycle from initial load through consent grant, revocation, and re-consent.

## Legal Background

Under DSGVO (GDPR), you **must not** set non-essential cookies or collect PII before the user gives explicit, informed consent. The toolbox stack enforces this:

| Requirement | How We Comply |
|---|---|
| No tracking before consent | PostHog starts in memory-only mode (zero cookies) |
| Informed consent | Clear banner explaining what data is collected |
| Granular control | Users can accept analytics separately from error tracking |
| Right to withdraw | `revokeConsent()` clears all tracking data instantly |
| Data sovereignty | All services self-hosted — no data leaves your server |
| Legitimate interest | Sentry error tracking can work without cookies (stripped PII) |

## The Three States

### State 1: No Consent Yet (first visit)

```
User visits site/opens app
         │
         ▼
┌─────────────────────────┐
│ PostHog: persistence     │
│   = 'memory'             │  ← Nothing written to disk/cookies
│   autocapture = false    │  ← No automatic DOM tracking
│   capture_pageview: true │  ← Anonymous pageview only
│                          │
│ Sentry: active           │
│   sendDefaultPii = false │  ← Errors captured, no user data
│   beforeSend: strip user │  ← Headers, cookies removed
│                          │
│ Unleash: active          │  ← Feature flags always work
│   (no PII involved)      │     (stateless evaluation)
└─────────────────────────┘
```

**What IS collected without consent:**
- Anonymous pageview count (no user ID, no session)
- Error stack traces (without user context, IP, headers)
- Feature flag evaluations (stateless, no user data)

**What is NOT collected without consent:**
- Cookies of any kind
- localStorage entries (except the consent preference itself)
- User identification
- Autocaptured DOM interactions
- Session recordings
- IP addresses in analytics
- Request headers in Sentry

### State 2: Consent Granted

When the user clicks "Accept All" or enables analytics in settings:

```javascript
// Web (Astro / Next.js)
function grantConsent() {
  // 1. Save preference
  localStorage.setItem('toolbox_consent', 'granted');
  localStorage.setItem('toolbox_consent_details', JSON.stringify({
    analytics: true,
    errorTracking: true,
    timestamp: new Date().toISOString()
  }));

  // 2. Upgrade PostHog
  posthog.set_config({
    persistence: 'localStorage+cookie',
    autocapture: true,
  });
  posthog.opt_in_capturing();

  // 3. PostHog now:
  //    - Sets cookies (ph_<project>_posthog)
  //    - Uses localStorage for session data
  //    - Autocaptures clicks, inputs, page views
  //    - Enables session recordings (if configured)
  //    - Identifies users across sessions

  // 4. Sentry upgrades
  //    - beforeSend stops stripping user data
  //    - PII (user, headers, cookies) included in error reports
  //    - Session replay sample rate increases

  // 5. Dispatch event so Sentry listener picks it up
  window.dispatchEvent(new CustomEvent('toolbox:consent', {
    detail: { granted: true }
  }));
}
```

```dart
// Flutter
Future<void> grantConsent() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool('toolbox_consent_granted', true);

  // PostHog opts in
  Posthog().optIn();
  // Now tracking with device persistence

  // Sentry can set user
  Sentry.configureScope((scope) {
    scope.setUser(SentryUser(id: userId));
  });
}
```

```swift
// Swift
func grantConsent() {
  UserDefaults.standard.set(true, forKey: "toolbox_consent_granted")

  PostHogSDK.shared.optIn()
  // Full tracking with device persistence

  ErrorTracker.setUser(userId: currentUserId)
}
```

**What changes after consent:**

| Aspect | Before Consent | After Consent |
|---|---|---|
| PostHog persistence | `memory` (RAM only) | `localStorage+cookie` |
| Autocapture | Disabled | Enabled |
| Session recording | Disabled | Enabled (if configured) |
| User identification | Anonymous | Persistent cross-session |
| Sentry user context | Stripped | Included (IP, user ID) |
| Sentry breadcrumbs | Technical only | UI interactions included |
| Cookies set | Zero | PostHog session cookie |

### State 3: Consent Revoked

When the user revokes consent (from settings or a "manage cookies" link):

```javascript
// Web
function revokeConsent() {
  // 1. Update preference
  localStorage.setItem('toolbox_consent', 'denied');

  // 2. Opt out PostHog
  posthog.opt_out_capturing();

  // 3. Clear ALL PostHog data
  // Cookies
  document.cookie.split(';').forEach(cookie => {
    const name = cookie.split('=')[0].trim();
    if (name.startsWith('ph_')) {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }
  });

  // localStorage
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith('ph_')) {
      localStorage.removeItem(key);
    }
  });

  // 4. Reconfigure PostHog to memory mode
  posthog.set_config({
    persistence: 'memory',
    autocapture: false,
  });

  // 5. Clear Sentry user
  Sentry.setUser(null);

  // 6. Notify Sentry listener
  window.dispatchEvent(new CustomEvent('toolbox:consent', {
    detail: { granted: false }
  }));
}
```

**After revocation:**
- All PostHog cookies deleted
- All PostHog localStorage entries removed
- PostHog back to memory mode (anonymous)
- Sentry user context cleared
- Subsequent pageviews are anonymous again
- No new cookies will be set

## Implementation Per Platform

### Web: Cookie Consent Banner

The `CookieConsent` component (shared pattern across Astro and Next.js):

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  We use cookies to improve your experience.              │
│                                                          │
│  We use analytics to understand how you use our site     │
│  and error tracking to fix issues. All data stays on     │
│  our own servers (EU).                                   │
│                                                          │
│  ┌────────────┐  ┌──────────────────┐  ┌──────────┐    │
│  │ Accept All  │  │ Only Essential   │  │ Settings  │    │
│  └────────────┘  └──────────────────┘  └──────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘

Settings expanded:
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ☑ Essential (always active)                             │
│    Required for the site to function.                    │
│                                                          │
│  ☐ Analytics                                             │
│    Helps us understand how you use the site.             │
│    Provider: PostHog (self-hosted, EU)                   │
│                                                          │
│  ☐ Error Tracking                                        │
│    Helps us fix bugs faster.                             │
│    Provider: Sentry (self-hosted, EU)                    │
│                                                          │
│  ┌──────────────────┐                                    │
│  │ Save Preferences  │                                   │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
```

### Mobile: Consent Dialog

On mobile (Flutter/Swift), a full-screen or bottom-sheet consent dialog appears on first launch. The same three options (Accept All / Essential / Customize) with toggle switches for granular control.

Key difference from web: mobile apps use `SharedPreferences` (Flutter) or `UserDefaults` (Swift) instead of cookies. There are no cookies involved in mobile apps — the consent controls **SDK persistence** and **PII collection**.

## Handling Granular Consent

When a user customizes their consent (e.g., analytics yes, error tracking no):

```javascript
const details = {
  analytics: true,       // PostHog enabled
  errorTracking: false,  // Sentry PII stays disabled
  timestamp: new Date().toISOString()
};
localStorage.setItem('toolbox_consent_details', JSON.stringify(details));

// Apply selectively
if (details.analytics) {
  posthog.opt_in_capturing();
  posthog.set_config({ persistence: 'localStorage+cookie', autocapture: true });
} else {
  posthog.opt_out_capturing();
  posthog.set_config({ persistence: 'memory', autocapture: false });
}

// Sentry always captures errors (legitimate interest),
// but PII is only included when errorTracking is true
window.__toolbox_error_tracking_consent = details.errorTracking;
```

## Re-Consent and "Manage Cookies" Link

DSGVO requires that users can **change their mind at any time**. Include a "Manage Cookies" or "Privacy Settings" link in your footer/settings:

```html
<!-- Web: footer link -->
<a href="#" onclick="document.getElementById('cookie-consent').style.display='block'">
  Privacy Settings
</a>
```

```dart
// Flutter: in settings
ListTile(
  title: Text('Privacy & Consent'),
  onTap: () => Navigator.push(context,
    MaterialPageRoute(builder: (_) => SettingsScreen())),
)
```

## Server-Side Analytics (FastAPI)

For backend APIs, cookie consent is a **client-side concern**. The server:

1. Receives a `X-Consent: granted` or `X-Consent: denied` header from the client
2. When `granted`: includes user ID and metadata in PostHog events
3. When `denied` or missing: tracks anonymously, strips PII

```python
# FastAPI middleware reads the header
consent = request.headers.get("X-Consent", "denied")
if consent == "granted":
    analytics.track_event(user_id, "api_request", {"path": path})
else:
    analytics.track_event("anonymous", "api_request", {"path": path})
```

## PostHog Cookieless Mode — Technical Details

When PostHog runs in `persistence: 'memory'` mode:

- **No cookies** are set (`ph_<token>_posthog` cookie does NOT exist)
- **No localStorage** entries are written
- **No sessionStorage** is used
- Session state exists only in JavaScript memory — lost on page reload
- Each pageview is treated as a new anonymous user
- Events still reach PostHog but cannot be linked across pages/sessions
- Useful for: anonymous aggregate analytics (total pageviews, popular pages)

When switched to `persistence: 'localStorage+cookie'`:

- A `ph_<token>_posthog` cookie is set (stores distinct_id, session_id)
- Additional data in localStorage (feature flags cache, etc.)
- Sessions are linked across pages and visits
- User can be identified across sessions
- Full funnel analysis, retention, and cohort features work

## Checklist for DSGVO Compliance

- [ ] Cookie banner shows **before** any non-essential cookies are set
- [ ] PostHog starts in `persistence: 'memory'` mode
- [ ] Sentry starts with `sendDefaultPii: false`
- [ ] "Accept All" explicitly enables tracking
- [ ] "Only Essential" keeps everything anonymous
- [ ] "Customize" allows granular control
- [ ] User can change their mind at any time (footer link / settings)
- [ ] Revoking consent **deletes** all tracking cookies and localStorage
- [ ] Consent choice is recorded with timestamp
- [ ] All data processing happens on your own servers (EU)
- [ ] Privacy policy links to specific services and their data handling
- [ ] No third-party scripts loaded before consent (Google Analytics, Facebook Pixel, etc.)
