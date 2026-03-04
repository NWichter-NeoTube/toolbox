/**
 * Playwright smoke tests for the Next.js webapp boilerplate.
 *
 * Run with:
 *   bun run build && bun run test:e2e
 */

import { test, expect } from "@playwright/test";

test.describe("Smoke tests", () => {
  test("page loads and displays heading", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Toolbox App/);
    await expect(
      page.getByRole("heading", { name: "Toolbox Web App" }),
    ).toBeVisible();
  });

  test("cookie consent banner is visible on first visit", async ({ page }) => {
    // Clear any prior consent state.
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("toolbox_consent");
      localStorage.removeItem("toolbox_consent_details");
    });
    await page.reload();

    const banner = page.getByRole("dialog", { name: "Cookie consent" });
    await expect(banner).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Accept All" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Only Essential" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Settings" })).toBeVisible();
  });

  test("accepting cookies hides the banner and stores consent", async ({
    page,
  }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("toolbox_consent");
      localStorage.removeItem("toolbox_consent_details");
    });
    await page.reload();

    const banner = page.getByRole("dialog", { name: "Cookie consent" });
    await expect(banner).toBeVisible();

    await page.getByRole("button", { name: "Accept All" }).click();

    // Banner should disappear.
    await expect(banner).not.toBeVisible();

    // Consent should be stored in localStorage.
    const consent = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent"),
    );
    expect(consent).toBe("granted");

    const details = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent_details"),
    );
    expect(JSON.parse(details!)).toEqual({ analytics: true, errors: true });
  });

  test("rejecting cookies hides the banner and stores denial", async ({
    page,
  }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("toolbox_consent");
      localStorage.removeItem("toolbox_consent_details");
    });
    await page.reload();

    await page.getByRole("button", { name: "Only Essential" }).click();

    const banner = page.getByRole("dialog", { name: "Cookie consent" });
    await expect(banner).not.toBeVisible();

    const consent = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent"),
    );
    expect(consent).toBe("denied");
  });

  test("settings panel allows granular consent", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("toolbox_consent");
      localStorage.removeItem("toolbox_consent_details");
    });
    await page.reload();

    // Open settings.
    await page.getByRole("button", { name: "Settings" }).click();
    await expect(page.getByText("Cookie Settings")).toBeVisible();

    // Toggle analytics on, leave errors off.
    const analyticsCheckbox = page.locator('input[type="checkbox"]').nth(1);
    await analyticsCheckbox.check();

    await page.getByRole("button", { name: "Save Preferences" }).click();

    const banner = page.getByRole("dialog", { name: "Cookie consent" });
    await expect(banner).not.toBeVisible();

    const details = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent_details"),
    );
    expect(JSON.parse(details!)).toEqual({ analytics: true, errors: false });
  });

  test("health check API returns 200", async ({ request }) => {
    const response = await request.get("/api/health");
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe("ok");
    expect(body.timestamp).toBeDefined();
  });

  test("banner does not reappear after consent is given", async ({ page }) => {
    await page.goto("/");

    // Simulate prior consent.
    await page.evaluate(() => {
      localStorage.setItem("toolbox_consent", "granted");
      localStorage.setItem(
        "toolbox_consent_details",
        JSON.stringify({ analytics: true, errors: true }),
      );
    });
    await page.reload();

    const banner = page.getByRole("dialog", { name: "Cookie consent" });
    await expect(banner).not.toBeVisible();
  });
});
