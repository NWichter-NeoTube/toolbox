"use client";

/**
 * React context provider for consent-aware PostHog analytics.
 *
 * Wraps the application in `layout.tsx` and provides:
 *  - Automatic PostHog initialisation on mount.
 *  - Automatic page-view tracking on route changes (Next.js App Router).
 *  - Consent management functions via the `useAnalytics()` hook.
 */

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { usePathname, useSearchParams } from "next/navigation";
import type { PostHog } from "posthog-js";
import {
  initAnalytics,
  grantConsent as _grantConsent,
  revokeConsent as _revokeConsent,
  hasConsent as _hasConsent,
  getConsentState,
  posthog as posthogInstance,
  type ConsentState,
} from "@/lib/analytics";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface AnalyticsContextValue {
  posthog: PostHog | null;
  grantConsent: () => void;
  revokeConsent: () => void;
  hasConsent: () => boolean;
  getConsentState: () => ConsentState;
}

const AnalyticsContext = createContext<AnalyticsContextValue>({
  posthog: null,
  grantConsent: () => {},
  revokeConsent: () => {},
  hasConsent: () => false,
  getConsentState: () => null,
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const initialised = useRef(false);

  // Initialise PostHog once on mount.
  useEffect(() => {
    if (initialised.current) return;
    initialised.current = true;
    initAnalytics();
  }, []);

  // Track page views on route changes.
  useEffect(() => {
    if (!posthogInstance) return;

    let url = window.origin + pathname;
    if (searchParams.toString()) {
      url += `?${searchParams.toString()}`;
    }

    posthogInstance.capture("$pageview", {
      $current_url: url,
    });
  }, [pathname, searchParams]);

  const value: AnalyticsContextValue = {
    posthog: posthogInstance ?? null,
    grantConsent: _grantConsent,
    revokeConsent: _revokeConsent,
    hasConsent: _hasConsent,
    getConsentState,
  };

  return (
    <AnalyticsContext.Provider value={value}>
      {children}
    </AnalyticsContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Access PostHog and consent management from any client component.
 *
 * ```tsx
 * const { posthog, grantConsent, revokeConsent, hasConsent } = useAnalytics();
 * ```
 */
export function useAnalytics(): AnalyticsContextValue {
  return useContext(AnalyticsContext);
}
