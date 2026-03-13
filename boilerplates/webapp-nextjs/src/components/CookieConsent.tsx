"use client";

/**
 * DSGVO/GDPR-compliant cookie consent banner.
 *
 * Behaviour:
 *  - On first visit the banner is shown at the bottom of the viewport.
 *  - "Accept All" -- grants full analytics & error-tracking consent.
 *  - "Only Essential" -- denies consent; analytics stays cookieless.
 *  - "Settings" -- expands a panel where the user can toggle analytics and
 *    error tracking independently.
 *  - The preference is persisted in localStorage ("toolbox_consent" and
 *    "toolbox_consent_details").
 *  - The banner does NOT appear again until the user clears storage or the
 *    consent state is reset.
 *
 * Uses inline styles (no Tailwind dependency).
 */

import { useEffect, useState } from "react";
import { useAnalytics } from "@/providers/AnalyticsProvider";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ConsentDetails {
  analytics: boolean;
  errors: boolean;
}

const DETAILS_KEY = "toolbox_consent_details";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function readDetails(): ConsentDetails | null {
  try {
    const raw = localStorage.getItem(DETAILS_KEY);
    return raw ? (JSON.parse(raw) as ConsentDetails) : null;
  } catch {
    return null;
  }
}

function writeDetails(details: ConsentDetails): void {
  try {
    localStorage.setItem(DETAILS_KEY, JSON.stringify(details));
  } catch {
    // Ignore.
  }
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = {
  wrapper: {
    position: "fixed" as const,
    insetInline: 0,
    bottom: 0,
    zIndex: 9999,
    display: "flex",
    justifyContent: "center",
    padding: "1rem",
    pointerEvents: "none" as const,
  },
  container: {
    pointerEvents: "auto" as const,
    width: "100%",
    maxWidth: "48rem",
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "0.75rem",
    boxShadow: "0 -4px 24px rgb(0 0 0 / 0.08)",
    padding: "1.25rem 1.5rem",
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: "0.9rem",
    color: "#1a202c",
    lineHeight: 1.5,
  },
  banner: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "1rem",
  },
  text: {
    margin: 0,
  },
  actions: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "0.5rem",
  },
  btnBase: {
    cursor: "pointer",
    border: "none",
    borderRadius: "0.5rem",
    padding: "0.55rem 1.25rem",
    fontSize: "0.875rem",
    fontWeight: 600,
    transition: "background 0.15s, color 0.15s",
    fontFamily: "inherit",
  },
  btnPrimary: {
    background: "#2563eb",
    color: "#fff",
  },
  btnSecondary: {
    background: "#f1f5f9",
    color: "#334155",
  },
  btnLink: {
    background: "none",
    color: "#2563eb",
    paddingInline: "0.5rem",
    textDecoration: "underline",
    textUnderlineOffset: "2px",
  },
  settingsTitle: {
    margin: "0 0 0.75rem",
    fontSize: "1rem",
  },
  settingsGroup: {
    padding: "0.5rem 0",
    borderTop: "1px solid #e2e8f0",
  },
  toggle: {
    display: "flex",
    alignItems: "flex-start" as const,
    gap: "0.75rem",
    cursor: "pointer",
    border: "none",
    background: "none",
    textAlign: "left" as const,
    padding: 0,
    font: "inherit",
    color: "inherit",
    width: "100%",
  },
  checkbox: {
    marginTop: "0.25rem",
    width: "1.1rem",
    height: "1.1rem",
    accentColor: "#2563eb",
  },
  toggleLabel: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.15rem",
  },
  toggleSmall: {
    color: "#64748b",
    fontSize: "0.8rem",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CookieConsent() {
  const { grantConsent, revokeConsent, hasConsent } = useAnalytics();
  const [visible, setVisible] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [analyticsChecked, setAnalyticsChecked] = useState(false);
  const [errorsChecked, setErrorsChecked] = useState(false);

  // Show the banner only if no consent decision has been recorded yet.
  useEffect(() => {
    const consentValue = localStorage.getItem("toolbox_consent");
    const details = readDetails();

    if (details === null && consentValue === null) {
      setVisible(true);
    }

    // Pre-fill settings checkboxes from any prior selection.
    if (details) {
      setAnalyticsChecked(details.analytics);
      setErrorsChecked(details.errors);
    }
  }, []);

  // -------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------

  function applyConsent(details: ConsentDetails) {
    writeDetails(details);

    if (details.analytics) {
      grantConsent();
    } else {
      revokeConsent();
    }

    setVisible(false);
  }

  function handleAcceptAll() {
    applyConsent({ analytics: true, errors: true });
  }

  function handleRejectAll() {
    applyConsent({ analytics: false, errors: false });
  }

  function handleSavePreferences() {
    applyConsent({ analytics: analyticsChecked, errors: errorsChecked });
  }

  // -------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      aria-modal="false"
      style={styles.wrapper}
    >
      <div style={styles.container}>
        {!showSettings ? (
          /* Main banner */
          <div style={styles.banner}>
            <div>
              <p style={styles.text}>
                We use cookies and similar technologies to improve your
                experience and analyse usage. You can accept all cookies, choose
                only essential ones, or customise your preferences.
              </p>
            </div>
            <div style={styles.actions}>
              <button
                type="button"
                style={{ ...styles.btnBase, ...styles.btnPrimary }}
                onClick={handleAcceptAll}
              >
                Accept All
              </button>
              <button
                type="button"
                style={{ ...styles.btnBase, ...styles.btnSecondary }}
                onClick={handleRejectAll}
              >
                Only Essential
              </button>
              <button
                type="button"
                style={{ ...styles.btnBase, ...styles.btnLink }}
                onClick={() => setShowSettings(true)}
              >
                Settings
              </button>
            </div>
          </div>
        ) : (
          /* Granular settings panel */
          <div>
            <h3 style={styles.settingsTitle}>Cookie Settings</h3>

            {/* Essential -- always on */}
            <div style={styles.settingsGroup}>
              <label style={styles.toggle}>
                <input
                  type="checkbox"
                  disabled
                  checked
                  style={styles.checkbox}
                />
                <span style={styles.toggleLabel}>
                  <strong>Essential</strong>
                  <small style={styles.toggleSmall}>
                    Required for the website to function. Cannot be disabled.
                  </small>
                </span>
              </label>
            </div>

            {/* Analytics */}
            <div style={styles.settingsGroup}>
              <label style={styles.toggle}>
                <input
                  type="checkbox"
                  checked={analyticsChecked}
                  onChange={(e) => setAnalyticsChecked(e.target.checked)}
                  style={styles.checkbox}
                />
                <span style={styles.toggleLabel}>
                  <strong>Analytics</strong>
                  <small style={styles.toggleSmall}>
                    Helps us understand how visitors interact with the site
                    (Umami).
                  </small>
                </span>
              </label>
            </div>

            {/* Error Tracking */}
            <div style={styles.settingsGroup}>
              <label style={styles.toggle}>
                <input
                  type="checkbox"
                  checked={errorsChecked}
                  onChange={(e) => setErrorsChecked(e.target.checked)}
                  style={styles.checkbox}
                />
                <span style={styles.toggleLabel}>
                  <strong>Error Tracking</strong>
                  <small style={styles.toggleSmall}>
                    Sends detailed error reports to help us fix bugs faster
                    (GlitchTip).
                  </small>
                </span>
              </label>
            </div>

            <div style={{ ...styles.actions, marginTop: "0.75rem" }}>
              <button
                type="button"
                style={{ ...styles.btnBase, ...styles.btnPrimary }}
                onClick={handleSavePreferences}
              >
                Save Preferences
              </button>
              <button
                type="button"
                style={{ ...styles.btnBase, ...styles.btnLink }}
                onClick={() => setShowSettings(false)}
              >
                Back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
