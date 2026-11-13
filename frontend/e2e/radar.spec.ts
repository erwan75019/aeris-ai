import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const screenshots = "../docs/qa";

test("radar loads real API data and supports the critical analysis journey", async ({ page }) => {
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => failedRequests.push(request.url()));

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Live Airspace" })).toBeVisible();
  await expect(page.getByText("Synthetic demo", { exact: true })).toBeVisible();
  await expect(page.getByText("API connected")).toBeVisible();
  await expect(page.locator(".aircraft-marker")).toHaveCount(4);

  const search = page.getByLabel("Search callsign or ICAO24");
  await search.fill("AER101");
  await expect(page.locator(".aircraft-marker")).toHaveCount(1);
  const aircraft = page.getByRole("button", { name: "Select AER101" });
  await aircraft.focus();
  await expect(aircraft).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "AER101" })).toBeVisible();
  await expect(page.getByText(/transformer · uncertainty/)).toBeVisible();

  await page.getByRole("button", { name: "Analyze flight" }).click();
  await expect(page.getByText(/Track contains 61 synthetic_demo states/)).toBeVisible();
  await expect(page.locator(".agent-strip span")).toHaveCount(4);

  await page.getByLabel("Replay minute").fill("30");
  await expect(page.getByText("12:30:00 UTC", { exact: true }).first()).toBeVisible();

  const accessibility = await new AxeBuilder({ page }).analyze();
  const blockingViolations = accessibility.violations.filter((item) =>
    item.impact === "critical" || item.impact === "serious"
  );
  expect(blockingViolations).toEqual([]);
  expect(failedRequests).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("radar exposes loading, empty and recoverable error states", async ({ page }) => {
  const routePattern = "**/api/v1/replay/snapshot**";
  await page.route(routePattern, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [],
        meta: {
          mode: "demo",
          data_classification: "synthetic_demo",
          source: "aeris_demo",
          count: 0,
          generated_at: "2025-01-15T13:00:00Z",
          replay_at: "2025-01-15T13:00:00Z",
        },
      }),
    });
  });
  await page.goto("/");
  await expect(page.getByText("Updating positions…")).toBeVisible();
  await expect(page.getByText("No aircraft in this view")).toBeVisible();

  await page.unroute(routePattern);
  await page.route(routePattern, (route) => route.fulfill({ status: 503, body: "{}" }));
  await page.reload();
  await expect(page.locator(".error-banner")).toContainText("AERIS API returned 503");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
});

test("digital twin creates a bounded synthetic scenario", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/twin");

  await expect(page.getByRole("heading", { name: "Digital Twin" })).toBeVisible();
  await expect(page.getByText("Synthetic only", { exact: true })).toBeVisible();
  await expect(page.locator(".aircraft-marker")).toHaveCount(4);
  await expect(page.locator(".scenario-result code")).toContainText("sim-");

  await page.getByLabel("Anomaly type").selectOption("altitude_spike");
  await page.getByLabel("Scenario severity").fill("0.8");
  await page.getByLabel("Synthetic wind speed").fill("35");
  await expect(page.locator(".scenario-result")).toHaveCount(0);
  await page.getByRole("button", { name: "Run scenario" }).click();
  await expect(page.locator(".scenario-result")).toContainText("synthetic simulation");
  await expect(page.locator(".scenario-result")).toContainText("ML score before");
  await expect(page.locator(".scenario-result")).toContainText("ML score after");
  await expect(page.locator(".scenario-result")).toContainText("synthetic wind 35 kt");
  await expect(page.locator(".scenario-result")).toContainText("not a certified air-traffic simulator");

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.filter((item) =>
    item.impact === "critical" || item.impact === "serious"
  )).toEqual([]);
  await page.screenshot({
    path: `${screenshots}/digital-twin-1440x900.png`,
    fullPage: false,
    animations: "disabled",
  });
});

test("analytics renders API metrics and telemetry", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/analytics");

  await expect(page.getByRole("heading", { name: "Airspace Analytics" })).toBeVisible();
  await expect(page.locator(".metric-row article").first()).toContainText("4");
  await expect(page.getByRole("img", { name: "Aircraft altitude bar chart" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Regional traffic density" })).toBeVisible();
  await expect(page.getByText("random forest density")).toBeVisible();
  await expect(page.getByRole("img", { name: "Regional traffic density forecast chart" })).toBeVisible();
  await expect(page.getByText(/Held-out synthetic MAE/)).toBeVisible();
  await expect(page.locator(".analytics-row")).toHaveCount(5);
  await expect(page.getByRole("link", { name: /Radar/ })).toHaveAttribute("href", "/");

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.filter((item) =>
    item.impact === "critical" || item.impact === "serious"
  )).toEqual([]);
  await page.screenshot({
    path: `${screenshots}/analytics-1440x900.png`,
    fullPage: false,
    animations: "disabled",
  });
});

for (const viewport of [
  { name: "mobile-390x844", width: 390, height: 844 },
  { name: "tablet-768x900", width: 768, height: 900 },
  { name: "desktop-1440x900", width: 1440, height: 900 },
]) {
  test(`visual evidence ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await expect(page.locator(".aircraft-marker")).toHaveCount(4);
    await page.getByRole("button", { name: "Select AER101" }).click();
    await expect(page.getByRole("heading", { name: "AER101" })).toBeVisible();
    await page.screenshot({
      path: `${screenshots}/${viewport.name}.png`,
      fullPage: false,
      animations: "disabled",
    });
  });
}
