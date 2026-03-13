"use client";

/**
 * React context provider for ENV-based feature flags.
 *
 * Wraps the application in `layout.tsx` and provides:
 *  - `useFeatureFlag(name)` hook for boolean flag checks.
 *
 * Flags are read from NEXT_PUBLIC_FEATURE_* environment variables at build
 * time. No external service or async initialisation needed.
 */

import {
  createContext,
  useCallback,
  useContext,
  type ReactNode,
} from "react";
import { isFeatureEnabled } from "@/lib/feature-flags";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface FeatureFlagContextValue {
  /** Check if a feature flag is enabled. */
  isEnabled: (flagName: string) => boolean;
}

const FeatureFlagContext = createContext<FeatureFlagContextValue>({
  isEnabled: () => false,
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function FeatureFlagProvider({ children }: { children: ReactNode }) {
  const isEnabledCb = useCallback(
    (flagName: string) => isFeatureEnabled(flagName),
    [],
  );

  return (
    <FeatureFlagContext.Provider value={{ isEnabled: isEnabledCb }}>
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
 * const showDarkMode = useFeatureFlag("dark_mode");
 * ```
 */
export function useFeatureFlag(flagName: string): boolean {
  const ctx = useContext(FeatureFlagContext);
  return ctx.isEnabled(flagName);
}
