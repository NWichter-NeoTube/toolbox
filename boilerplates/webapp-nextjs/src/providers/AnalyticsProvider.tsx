"use client";

/**
 * React context provider for consent-aware Umami analytics.
 *
 * Wraps the application in `layout.tsx` and provides:
 *  - Umami script injection (only when consent is granted).
 *  - Automatic page-view tracking on route changes (Next.js App Router).
 *  - Consent management functions via the `useAnalytics()` hook.
 */

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useSearchParams } from "next/navigation";
import Script from "next/script";
import {
  hasConsent as _hasConsent,
  grantConsent as _grantConsent,
  revokeConsent as _revokeConsent,
  trackPageview,
  getUmamiScriptUrl,
  getUmamiWebsiteId,
} from "@/lib/analytics";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface AnalyticsContextValue {
  grantConsent: () => void;
  revokeConsent: () => void;
  hasConsent: () => boolean;
}

const AnalyticsContext = createContext<AnalyticsContextValue>({
  grantConsent: () => {},
  revokeConsent: () => {},
  hasConsent: () => false,
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [consentGranted, setConsentGranted] = useState(false);
  const initialised = useRef(false);

  // Check consent on mount.
  useEffect(() => {
    if (initialised.current) return;
    initialised.current = true;
    setConsentGranted(_hasConsent());
  }, []);

  // Listen for consent changes.
  useEffect(() => {
    function handleConsent(e: Event) {
      const detail = (e as CustomEvent<string>).detail;
      setConsentGranted(detail === "granted");
    }
    window.addEventListener("toolbox:consent", handleConsent);
    return () => window.removeEventListener("toolbox:consent", handleConsent);
  }, []);

  // Track page views on route changes.
  useEffect(() => {
    if (!consentGranted) return;

    let url = pathname;
    if (searchParams.toString()) {
      url += `?${searchParams.toString()}`;
    }

    trackPageview(url);
  }, [pathname, searchParams, consentGranted]);

  const scriptUrl = getUmamiScriptUrl();
  const websiteId = getUmamiWebsiteId();

  const value: AnalyticsContextValue = {
    grantConsent: _grantConsent,
    revokeConsent: _revokeConsent,
    hasConsent: _hasConsent,
  };

  return (
    <AnalyticsContext.Provider value={value}>
      {consentGranted && scriptUrl && websiteId && (
        <Script
          async
          src={scriptUrl}
          data-website-id={websiteId}
          strategy="afterInteractive"
        />
      )}
      {children}
    </AnalyticsContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Access consent management from any client component.
 *
 * ```tsx
 * const { grantConsent, revokeConsent, hasConsent } = useAnalytics();
 * ```
 */
export function useAnalytics(): AnalyticsContextValue {
  return useContext(AnalyticsContext);
}
