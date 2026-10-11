import { expect, test, type Page } from "@playwright/test";

type DashboardSummary = {
  inventory_in_stock: number;
  inventory_issued: number;
  pending_component_requests: number;
  backordered_quantity: number;
  drones_in_production: number;
  confirmed_drones: number;
  open_production_tasks: number;
  my_attendance_days_last_30: number;
  my_attendance_today_status: string | null;
  recent_audit_events: [];
};

const failureTestsEnabled = process.env.GOAG_E2E_FAILURES === "1";
const password = process.env.GOAG_TEST_PASSWORD || "";
const email = process.env.GOAG_TEST_STORE_MANAGER_EMAIL || "store.manager@goag.example";

const healthySummary: DashboardSummary = {
  inventory_in_stock: 4,
  inventory_issued: 1,
  pending_component_requests: 0,
  backordered_quantity: 0,
  drones_in_production: 1,
  confirmed_drones: 2,
  open_production_tasks: 0,
  my_attendance_days_last_30: 3,
  my_attendance_today_status: "present",
  recent_audit_events: [],
};

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(password);
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(page).toHaveURL(/\/dashboard(?:$|\/)/, { timeout: 30_000 });
}

function requireOptInCredentials() {
  if (failureTestsEnabled && !password) {
    throw new Error("GOAG_E2E_FAILURES=1 requires GOAG_TEST_PASSWORD.");
  }
}

test.describe("GOAG overview failure states", () => {
  test("shows a retryable error after a controlled 503 and recovers", async ({ page }) => {
    test.skip(!failureTestsEnabled, "Set GOAG_E2E_FAILURES=1 to run deterministic failure-state coverage.");
    requireOptInCredentials();

    await signIn(page);
    let attempts = 0;
    let allowRecovery = false;
    await page.route("**/api/backend/dashboard/summary", async (route) => {
      attempts += 1;
      if (!allowRecovery) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Controlled test outage" }),
        });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(healthySummary) });
    });

    await page.goto("/dashboard");
    await expect(page.getByText("Operational data is unavailable", { exact: true })).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Controlled test outage")).toBeVisible();

    allowRecovery = true;
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(page.getByText("Stock on hand")).toBeVisible({ timeout: 5_000 });
    expect(attempts).toBeGreaterThanOrEqual(2);
  });

  test("shows a retryable error when the summary exceeds the client timeout", async ({ page }) => {
    test.setTimeout(20_000);
    test.skip(!failureTestsEnabled, "Set GOAG_E2E_FAILURES=1 to run deterministic failure-state coverage.");
    requireOptInCredentials();

    await signIn(page);
    await page.route("**/api/backend/dashboard/summary", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 12_000));
      try {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(healthySummary) });
      } catch {
        // The browser has already aborted the request after the 8-second client timeout.
      }
    });

    await page.goto("/dashboard");
    await expect(page.getByText("Operational data is unavailable", { exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("took too long to respond")).toBeVisible();
  });
});
