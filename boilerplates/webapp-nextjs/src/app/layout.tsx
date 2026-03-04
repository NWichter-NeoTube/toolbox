import type { Metadata } from "next";
import { Suspense } from "react";
import { AnalyticsProvider } from "@/providers/AnalyticsProvider";
import { FeatureFlagProvider } from "@/providers/FeatureFlagProvider";
import { CookieConsent } from "@/components/CookieConsent";

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: {
    default: "Toolbox App",
    template: "%s | Toolbox App",
  },
  description: "Self-hosted SaaS toolbox web application.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
  ),
};

// ---------------------------------------------------------------------------
// Root layout
// ---------------------------------------------------------------------------

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Suspense fallback={null}>
          <AnalyticsProvider>
            <FeatureFlagProvider>
              {children}
              <CookieConsent />
            </FeatureFlagProvider>
          </AnalyticsProvider>
        </Suspense>
      </body>
    </html>
  );
}
