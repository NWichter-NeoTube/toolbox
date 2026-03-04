"use client";

/**
 * React context provider for Unleash feature flags.
 *
 * Wraps the application in `layout.tsx` and provides:
 *  - Automatic Unleash client initialisation on mount.
 *  - `useFeatureFlag(name)` hook for boolean flag checks.
 *  - `useVariant(name)` hook for variant payloads (A/B tests).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  initFeatureFlags,
  isEnabled,
  getVariant,
  getClient,
} from "@/lib/feature-flags";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface FeatureFlagContextValue {
  /** Whether the Unleash client has finished loading its initial payload. */
  ready: boolean;
  /** Check if a feature flag is enabled. */
  isEnabled: (flagName: string) => boolean;
  /** Get the variant for a feature flag. */
  getVariant: (flagName: string) => ReturnType<typeof getVariant>;
}

const FeatureFlagContext = createContext<FeatureFlagContextValue>({
  ready: false,
  isEnabled: () => false,
  getVariant: () => undefined,
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function FeatureFlagProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [, setTick] = useState(0);
  const initialised = useRef(false);

  useEffect(() => {
    if (initialised.current) return;
    initialised.current = true;

    initFeatureFlags().then(() => {
      setReady(true);

      // Subscribe to flag updates so components re-render when flags change.
      const client = getClient();
      if (client) {
        client.on("update", () => {
          setTick((t) => t + 1);
        });
      }
    });
  }, []);

  const isEnabledCb = useCallback(
    (flagName: string) => isEnabled(flagName),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ready],
  );

  const getVariantCb = useCallback(
    (flagName: string) => getVariant(flagName),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ready],
  );

  return (
    <FeatureFlagContext.Provider
      value={{ ready, isEnabled: isEnabledCb, getVariant: getVariantCb }}
    >
      {children}
    </FeatureFlagContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Check if a feature flag is enabled.
 *
 * ```tsx
 * const showBeta = useFeatureFlag("beta-dashboard");
 * ```
 */
export function useFeatureFlag(flagName: string): boolean {
  const ctx = useContext(FeatureFlagContext);
  return ctx.isEnabled(flagName);
}

/**
 * Get the variant payload for a feature flag.
 *
 * ```tsx
 * const variant = useVariant("checkout-experiment");
 * ```
 */
export function useVariant(flagName: string) {
  const ctx = useContext(FeatureFlagContext);
  return ctx.getVariant(flagName);
}
