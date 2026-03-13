import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import sentry from "@sentry/astro";

export default defineConfig({
  site: process.env.PUBLIC_SITE_URL || "https://www.example.com",
  output: "static",

  integrations: [
    sitemap(),
    sentry({
      dsn: process.env.PUBLIC_GLITCHTIP_DSN,
      sourceMapsUploadOptions: {
        enabled: !!process.env.GLITCHTIP_AUTH_TOKEN,
        project: process.env.GLITCHTIP_PROJECT,
        org: process.env.GLITCHTIP_ORG,
      },
      // Client-side SDK config — minimal by default, consent-aware setup
      // happens in src/lib/error-tracking.ts at runtime.
      clientInitPath: "src/lib/error-tracking.ts",
    }),
  ],

  vite: {
    define: {
      "import.meta.env.PUBLIC_UMAMI_HOST": JSON.stringify(
        process.env.PUBLIC_UMAMI_HOST ?? "",
      ),
      "import.meta.env.PUBLIC_UMAMI_WEBSITE_ID": JSON.stringify(
        process.env.PUBLIC_UMAMI_WEBSITE_ID ?? "",
      ),
    },
  },
});
