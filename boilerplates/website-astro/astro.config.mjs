import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import sentry from "@sentry/astro";

export default defineConfig({
  site: process.env.PUBLIC_SITE_URL || "https://www.example.com",
  output: "static",

  integrations: [
    sitemap(),
    sentry({
      dsn: process.env.PUBLIC_SENTRY_DSN,
      sourceMapsUploadOptions: {
        enabled: !!process.env.SENTRY_AUTH_TOKEN,
        project: process.env.SENTRY_PROJECT,
        org: process.env.SENTRY_ORG,
      },
      // Client-side SDK config — minimal by default, consent-aware setup
      // happens in src/lib/error-tracking.ts at runtime.
      clientInitPath: "src/lib/error-tracking.ts",
    }),
  ],

  vite: {
    define: {
      "import.meta.env.PUBLIC_POSTHOG_KEY": JSON.stringify(
        process.env.PUBLIC_POSTHOG_KEY ?? "",
      ),
      "import.meta.env.PUBLIC_POSTHOG_HOST": JSON.stringify(
        process.env.PUBLIC_POSTHOG_HOST ?? "",
      ),
      "import.meta.env.PUBLIC_UNLEASH_URL": JSON.stringify(
        process.env.PUBLIC_UNLEASH_URL ?? "",
      ),
      "import.meta.env.PUBLIC_UNLEASH_CLIENT_KEY": JSON.stringify(
        process.env.PUBLIC_UNLEASH_CLIENT_KEY ?? "",
      ),
    },
  },
});
