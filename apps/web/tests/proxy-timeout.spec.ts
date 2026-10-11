import { expect, test, type Page } from "@playwright/test";

const proxyTimeoutTestsEnabled = process.env.GOAG_E2E_PROXY_TIMEOUT === "1";
const password = process.env.GOAG_TEST_PASSWORD || "";
const email = process.env.GOAG_TEST_STORE_MANAGER_EMAIL || "store.manager@goag.example";

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill(password);
  await expect(page.getByLabel("Work email")).toHaveValue(email);
  await expect(page.getByLabel("Password")).toHaveValue(password);
  await page.getByRole("button", { name: "Sign in with password" }).click();
  await expect(page).toHaveURL(/\/dashboard(?:$|\/)/, { timeout: 30_000 });
}

test.describe("GOAG real proxy timeout", () => {
  test("returns a 504 when the FastAPI upstream exceeds the proxy timeout", async ({ page }) => {
    test.setTimeout(30_000);
    test.skip(!proxyTimeoutTestsEnabled, "Set GOAG_E2E_PROXY_TIMEOUT=1 to run the real proxy integration check.");
    if (!password) {
      throw new Error("GOAG_E2E_PROXY_TIMEOUT=1 requires GOAG_TEST_PASSWORD.");
    }

    await signIn(page);
    const response = await page.request.get("/api/backend/dashboard/summary");
    expect(response.status()).toBe(504);
    await expect(response.json()).resolves.toEqual({ detail: "The backend service timed out. Please retry." });
  });
});
