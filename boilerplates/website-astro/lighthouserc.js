/** @type {import('@lhci/cli').LighthouseConfig} */
module.exports = {
  ci: {
    collect: {
      // Run against the static build output served by Astro's preview server.
      startServerCommand: "bun run preview",
      startServerReadyPattern: "Local",
      url: ["http://localhost:4321/"],
      numberOfRuns: 3,
      settings: {
        // Use desktop preset for more stable scores in CI.
        preset: "desktop",
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.9 }],
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "categories:best-practices": ["error", { minScore: 0.9 }],
        "categories:seo": ["error", { minScore: 0.9 }],
      },
    },
    upload: {
      // By default just print results to stdout. Change to "lhci" when you
      // have a Lighthouse CI server running.
      target: "temporary-public-storage",
    },
  },
};
