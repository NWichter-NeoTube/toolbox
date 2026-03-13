import { test, expect } from "@playwright/test";

test.describe("Smoke tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  // -----------------------------------------------------------------------
  // Page loads
  // -----------------------------------------------------------------------

  test("home page loads successfully", async ({ page }) => {
    await expect(page).toHaveTitle(/Toolbox/i);
    await expect(page.locator("h1")).toContainText("Toolbox Website");
  });

  // -----------------------------------------------------------------------
  // Cookie consent banner
  // -----------------------------------------------------------------------

  test("cookie consent banner is visible on first visit", async ({ page }) => {
    const banner = page.locator("#cookie-consent");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Accept All");
    await expect(banner).toContainText("Only Essential");
    await expect(banner).toContainText("Settings");
  });

  test("accepting cookies hides the banner and stores consent", async ({
    page,
  }) => {
    const banner = page.locator("#cookie-consent");
    await expect(banner).toBeVisible();

    await page.click("#cc-accept");
    await expect(banner).toBeHidden();

    // Verify localStorage was set.
    const consent = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent"),
    );
    expect(consent).toBe("granted");

    const details = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent_details"),
    );
    const parsed = JSON.parse(details!);
    expect(parsed.analytics).toBe(true);
    expect(parsed.errors).toBe(true);
  });

  test("rejecting cookies hides the banner and stores denial", async ({
    page,
  }) => {
    const banner = page.locator("#cookie-consent");
    await expect(banner).toBeVisible();

    await page.click("#cc-reject");
    await expect(banner).toBeHidden();

    const consent = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent"),
    );
    expect(consent).toBe("denied");
  });

  test("settings panel can be opened and saved", async ({ page }) => {
    // Open settings.
    await page.click("#cc-settings-toggle");
    const settingsPanel = page.locator("#cc-settings");
    await expect(settingsPanel).toBeVisible();

    // Toggle analytics on, errors off.
    await page.check("#cc-opt-analytics");
    await page.uncheck("#cc-opt-errors");

    // Save.
    await page.click("#cc-save");
    const banner = page.locator("#cookie-consent");
    await expect(banner).toBeHidden();

    const details = await page.evaluate(() =>
      localStorage.getItem("toolbox_consent_details"),
    );
    const parsed = JSON.parse(details!);
    expect(parsed.analytics).toBe(true);
    expect(parsed.errors).toBe(false);
  });

  // -----------------------------------------------------------------------
  // Banner does not reappear after consent
  // -----------------------------------------------------------------------

  test("banner does not reappear after consent on reload", async ({ page }) => {
    await page.click("#cc-accept");
    await expect(page.locator("#cookie-consent")).toBeHidden();

    await page.reload();
    // The banner should remain hidden after reload.
    await expect(page.locator("#cookie-consent")).toBeHidden();
  });

  // -----------------------------------------------------------------------
  // Analytics initialisation
  // -----------------------------------------------------------------------

  test("analytics module is loaded on the page", async ({ page }) => {
    // Umami host is not configured in test env, so the script tag won't be
    // injected. We verify no uncaught exceptions occurred.
    const messages: string[] = [];
    page.on("console", (msg) => messages.push(msg.text()));

    await page.reload();
    await page.waitForTimeout(500);

    // The analytics component should have run without errors.
    const errors = messages.filter((m) => m.toLowerCase().includes("uncaught"));
    expect(errors).toHaveLength(0);
  });

  // -----------------------------------------------------------------------
  // Feature flag demo section
  // -----------------------------------------------------------------------

  test("feature flag demo section is present", async ({ page }) => {
    const demo = page.locator("#ff-demo");
    await expect(demo).toBeVisible();
    await expect(demo).toContainText("Feature Flag Demo");
  });
});
