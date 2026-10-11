import { expect, test, type Page } from "@playwright/test";

type RoleCase = {
  key: string;
  email: string;
  password: string;
  displayName: string;
  dashboardText: string;
  routes: Array<{ path: string; visibleText: string }>;
  forbiddenApiPrefixes?: string[];
};

const sharedPassword = process.env.GOAG_TEST_PASSWORD || "";
const runRequiredRoleMatrix = process.env.GOAG_RUN_ROLE_MATRIX === "1";

const roleCases: RoleCase[] = [
  {
    key: "managing-director",
    email: process.env.GOAG_TEST_MD_EMAIL || "md@goag.example",
    password: process.env.GOAG_TEST_MD_PASSWORD || "",
    displayName: "Managing Director",
    dashboardText: "Company-wide visibility across people, inventory, and production.",
    routes: [
      { path: "/dashboard/inventory", visibleText: "Director oversight" },
      { path: "/dashboard/production", visibleText: "Production control" },
      { path: "/dashboard/team", visibleText: "GOAG team members" },
      { path: "/dashboard/mailbox", visibleText: "GOAG mailbox" },
    ],
    forbiddenApiPrefixes: [],
  },
  {
    key: "production-manager",
    email: process.env.GOAG_TEST_PRODUCTION_MANAGER_EMAIL || "production.manager@goag.example",
    password: sharedPassword,
    displayName: "Production Manager",
    dashboardText: "Keep active drones, tasks, and completion decisions moving.",
    routes: [
      { path: "/dashboard/inventory", visibleText: "Production support" },
      { path: "/dashboard/production", visibleText: "Production control" },
      { path: "/dashboard/mailbox", visibleText: "Mailbox access unavailable" },
    ],
    forbiddenApiPrefixes: ["/api/backend/email", "/api/backend/admin"],
  },
  {
    key: "store-manager",
    email: process.env.GOAG_TEST_STORE_MANAGER_EMAIL || "store.manager@goag.example",
    password: sharedPassword,
    displayName: "Store Manager",
    dashboardText: "Keep stock accurate and component handovers ready for production.",
    routes: [
      { path: "/dashboard/inventory", visibleText: "Store control" },
      { path: "/dashboard/production", visibleText: "Production workspace unavailable" },
      { path: "/dashboard/mailbox", visibleText: "GOAG mailbox" },
    ],
    forbiddenApiPrefixes: ["/api/backend/production", "/api/backend/admin"],
  },
  {
    key: "sales-manager",
    email: process.env.GOAG_TEST_SALES_MANAGER_EMAIL || "sales.manager@goag.example",
    password: sharedPassword,
    displayName: "Sales Manager",
    dashboardText: "Sales workspace coming next",
    routes: [
      { path: "/dashboard/sales", visibleText: "Sales workspace coming next" },
      { path: "/dashboard/inventory", visibleText: "Inventory workspace unavailable" },
      { path: "/dashboard/mailbox", visibleText: "Mailbox access unavailable" },
    ],
    forbiddenApiPrefixes: [
      "/api/backend/inventory",
      "/api/backend/production",
      "/api/backend/email",
      "/api/backend/admin",
    ],
  },
  {
    key: "technician",
    email: process.env.GOAG_TEST_TECHNICIAN_EMAIL || "technician@goag.example",
    password: sharedPassword,
    displayName: "Technician",
    dashboardText: "Start with your assigned work, requests, and components.",
    routes: [
      { path: "/dashboard/inventory", visibleText: "Component handover" },
      { path: "/dashboard/production", visibleText: "Assigned production work" },
      { path: "/dashboard/team", visibleText: "Team administration unavailable" },
    ],
    forbiddenApiPrefixes: ["/api/backend/email", "/api/backend/admin"],
  },
  {
    key: "after-sales-manager",
    email: process.env.GOAG_TEST_AFTER_SALES_EMAIL || "after.sales@goag.example",
    password: sharedPassword,
    displayName: "After-Sales Manager",
    dashboardText: "After-sales workspace is not enabled yet",
    routes: [
      { path: "/dashboard", visibleText: "After-sales workspace is not enabled yet" },
      { path: "/dashboard/inventory", visibleText: "Inventory workspace unavailable" },
      { path: "/dashboard/production", visibleText: "Production workspace unavailable" },
      { path: "/dashboard/mailbox", visibleText: "Mailbox access unavailable" },
    ],
    forbiddenApiPrefixes: [
      "/api/backend/inventory",
      "/api/backend/production",
      "/api/backend/email",
      "/api/backend/admin",
    ],
  },
];

test.describe("GOAG seeded role matrix", () => {
  test.beforeAll(() => {
    if (!runRequiredRoleMatrix) return;
    const missing = roleCases.filter((role) => !role.password).map((role) => role.key);
    if (missing.length) {
      throw new Error(
        `GOAG_RUN_ROLE_MATRIX=1 requires credentials for every role. Missing: ${missing.join(", ")}`,
      );
    }
  });

  function trackApiRequests(page: Page): string[] {
    const requests: string[] = [];
    page.on("request", (request) => {
      const path = new URL(request.url()).pathname;
      if (path.startsWith("/api/backend/")) requests.push(path);
    });
    return requests;
  }

  function assertNoForbiddenApiRequests(role: RoleCase, requests: string[]) {
    const forbidden = (role.forbiddenApiPrefixes ?? []).filter((prefix) =>
      requests.some((requestPath) => requestPath.startsWith(prefix)),
    );
    expect(forbidden, `${role.key} made forbidden API requests: ${requests.join(", ")}`).toEqual([]);
  }

  async function signIn(page: Page, role: RoleCase) {
    // Wait for the client component to hydrate before filling controlled inputs.
    // Filling during the initial commit can be overwritten by React hydration.
    await page.goto("/login");
    await page.getByLabel("Work email").fill(role.email);
    await page.getByRole("textbox", { name: "Password" }).fill(role.password);
    await expect(page.getByLabel("Work email")).toHaveValue(role.email);
    await expect(page.getByRole("textbox", { name: "Password" })).toHaveValue(role.password);
    await page.getByRole("button", { name: "Sign in to workspace" }).click();
    await expect(page).toHaveURL(/\/dashboard(?:$|\/)/, { timeout: 30_000 });
    await expect(page.getByText(role.displayName, { exact: true }).first()).toBeVisible();
  }

  for (const role of roleCases) {
    test(`${role.key} can sign in and see its role overview`, async ({ page }) => {
      test.skip(!role.password, role.key === "managing-director" ? "Set GOAG_TEST_MD_PASSWORD for the Managing Director account." : "Set GOAG_TEST_PASSWORD before running the authenticated role matrix.");
      const requests = trackApiRequests(page);
      await signIn(page, role);
      await expect(page.getByText(role.dashboardText)).toBeVisible();
      assertNoForbiddenApiRequests(role, requests);
    });

    test(`${role.key} route permissions match the approved workspace matrix`, async ({ page }) => {
      test.skip(!role.password, role.key === "managing-director" ? "Set GOAG_TEST_MD_PASSWORD for the Managing Director account." : "Set GOAG_TEST_PASSWORD before running the authenticated role matrix.");
      const requests = trackApiRequests(page);
      await signIn(page, role);
      for (const route of role.routes) {
        await page.goto(route.path, { waitUntil: "commit" });
        await expect(page.getByText(route.visibleText, { exact: false }).first()).toBeVisible({ timeout: 15_000 });
      }
      assertNoForbiddenApiRequests(role, requests);
    });
  }
});
