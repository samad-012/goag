import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./apps/web/tests",
  testMatch: "proxy-timeout.spec.ts",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: "APP_ENV=test GOAG_TEST_PROXY_DELAY_MS=11000 UV_CACHE_DIR=/private/tmp/goag-uv-cache uv run uvicorn app.main:app --port 8001",
      cwd: "apps/api",
      url: "http://127.0.0.1:8001/healthz",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "GOAG_NEXT_DIST_DIR=.next-proxy-timeout API_BASE_URL=http://127.0.0.1:8001/api/v1 pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3001",
      url: "http://127.0.0.1:3001/login",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
