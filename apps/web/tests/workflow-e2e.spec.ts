import { expect, test, type Page } from "@playwright/test";

type BackendResult<T> = { status: number; body: T };
type BrowserRequestInit = Pick<RequestInit, "method" | "body" | "headers">;

const sharedPassword = process.env.GOAG_TEST_PASSWORD || "";
const workflowEnabled = process.env.GOAG_E2E_WORKFLOW === "1";
const storeEmail = process.env.GOAG_TEST_STORE_MANAGER_EMAIL || "store.manager@goag.example";
const productionEmail = process.env.GOAG_TEST_PRODUCTION_MANAGER_EMAIL || "production.manager@goag.example";

async function signIn(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByRole("textbox", { name: "Password" }).fill(sharedPassword);
  await page.getByRole("button", { name: "Sign in to workspace" }).click();
  await expect(page).toHaveURL(/\/dashboard(?:$|\/)/, { timeout: 30_000 });
}

async function backendRequest<T>(page: Page, path: string, init?: RequestInit): Promise<T> {
  const result = await page.evaluate(async ({ path, init }: { path: string; init?: BrowserRequestInit }) => {
    const response = await fetch(`/api/backend${path}`, {
      ...init,
      cache: "no-store",
      headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers },
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, body };
  }, { path, init: init ? { method: init.method, body: init.body, headers: init.headers } : undefined }) as BackendResult<T>;

  expect(result.status, `Backend request ${path} failed: ${JSON.stringify(result.body)}`).toBeLessThan(300);
  return result.body;
}

test.describe("GOAG serialized production workflow", () => {
  test("opening inventory through drone confirmation is traceable", async ({ browser }) => {
    test.setTimeout(120_000);
    test.skip(!workflowEnabled, "Set GOAG_E2E_WORKFLOW=1 to run the data-writing workflow test.");
    test.skip(!sharedPassword, "Set GOAG_TEST_PASSWORD before running the workflow test.");

    const storeContext = await browser.newContext();
    const productionContext = await browser.newContext();
    const storePage = await storeContext.newPage();
    const productionPage = await productionContext.newPage();
    const runId = Date.now().toString();
    const componentCode = `PW-E2E-${runId}`;
    const openingSerial = `${componentCode}-OPEN`;
    const delayedSerial = `${componentCode}-DELAYED`;
    const droneSerial = `PW-DRONE-${runId}`;

    try {
      await signIn(storePage, storeEmail);
      const component = await backendRequest<{ id: string }>(storePage, "/inventory/components", {
        method: "POST",
        body: JSON.stringify({ code: componentCode, name: `Playwright component ${runId}`, category: "E2E", serialized: true }),
      });
      const pendingUnit = await backendRequest<{ id: string }>(storePage, "/inventory/units", {
        method: "POST",
        body: JSON.stringify({ component_id: component.id, condition: "good", location: "store" }),
      });

      await storePage.goto("/dashboard/inventory");
      await expect(storePage.getByText("Opening inventory", { exact: true })).toBeVisible();
      await storePage.getByLabel("Component row 1").selectOption(component.id);
      await expect(storePage.getByLabel("Component row 1")).toHaveValue(component.id);
      await storePage.getByLabel("Serial number row 1").fill(openingSerial);
      await expect(storePage.getByLabel("Serial number row 1")).toHaveValue(openingSerial);
      await storePage.waitForTimeout(250);
      await storePage.getByText("Opening inventory", { exact: true }).click();
      await expect(storePage.getByText("Saved", { exact: true })).toBeVisible({ timeout: 15_000 });

      await signIn(productionPage, productionEmail);
      await productionPage.goto("/dashboard/production");
      await expect(productionPage.getByRole("heading", { name: "Production", exact: true })).toBeVisible();

      const models = await backendRequest<Array<{ id: string; code: string }>>(productionPage, "/production/drone-models");
      const drone = await backendRequest<{ id: string }>(productionPage, "/production/drones", {
        method: "POST",
        body: JSON.stringify({ drone_model_id: models[0]?.id ?? null, serial_number: droneSerial, notes: "Playwright workflow verification" }),
      });
      const request = await backendRequest<{ id: string; items: Array<{ id: string }> }>(productionPage, "/inventory/component-requests", {
        method: "POST",
        body: JSON.stringify({ drone_id: drone.id, items: [{ component_id: component.id, requested_quantity: 2 }] }),
      });
      const task = await backendRequest<{ id: string }>(productionPage, `/production/drones/${drone.id}/tasks`, {
        method: "POST",
        body: JSON.stringify({ title: "Complete Playwright workflow task" }),
      });

      await signIn(storePage, storeEmail);
      const partialIssue = await backendRequest<{ request_status: string; issue_line_ids: string[] }>(storePage, `/inventory/component-requests/${request.id}/issue`, {
        method: "POST",
        body: JSON.stringify({ lines: [{ request_item_id: request.items[0].id, quantity: 1, inventory_unit_ids: [pendingUnit.id] }] }),
      });
      expect(partialIssue.request_status).toBe("partially_issued");
      await backendRequest(storePage, `/inventory/units/${pendingUnit.id}/serial`, {
        method: "PATCH",
        body: JSON.stringify({ serial_number: delayedSerial }),
      });
      const completedIssue = await backendRequest<{ request_status: string; issue_line_ids: string[]; inventory_unit_ids: string[] }>(storePage, `/inventory/component-requests/${request.id}/issue`, {
        method: "POST",
        body: JSON.stringify({ lines: [{ request_item_id: request.items[0].id, quantity: 1, inventory_unit_ids: [] , serial_numbers: [openingSerial] }] }),
      });
      expect(completedIssue.request_status).toBe("fulfilled");

      await signIn(productionPage, productionEmail);
      await backendRequest(productionPage, `/production/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "completed" }),
      });
      for (const [issueLine, inventoryUnitId] of [[partialIssue.issue_line_ids[0], pendingUnit.id], [completedIssue.issue_line_ids[0], completedIssue.inventory_unit_ids[0]]] as const) {
        await backendRequest(productionPage, `/production/drones/${drone.id}/components`, {
          method: "POST",
          body: JSON.stringify({ action: "install", issue_line_id: issueLine, inventory_unit_id: inventoryUnitId }),
        });
      }
      await backendRequest(productionPage, `/production/drones/${drone.id}/confirm`, {
        method: "POST",
        body: JSON.stringify({ checklist: {
          required_components_installed: true,
          component_quantities_correct: true,
          serial_numbers_recorded: true,
          production_tasks_completed: true,
          component_issues_resolved: true,
          drone_serial_exists: true,
          quality_checklist_completed: true,
        } }),
      });

      await productionPage.goto("/dashboard/production");
      await expect(productionPage.getByText(droneSerial, { exact: true }).first()).toBeVisible();
      await expect(productionPage.getByText("Installation history", { exact: true })).toBeVisible();
      await expect(productionPage.getByText("Reopen confirmed drone", { exact: true })).toBeVisible();
    } finally {
      await storeContext.close();
      await productionContext.close();
    }
  });
});
