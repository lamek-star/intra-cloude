import { defineConfig, devices } from "@playwright/test";

// Runs against the real Docker Compose stack (docker-compose.yml's proxy
// service, Caddy with its internal-CA cert) -- not a mocked backend. Start
// the stack first: `docker compose up -d`. `ignoreHTTPSErrors` is needed
// because that cert is Caddy's internal CA, not a publicly trusted one --
// exactly what a local-first deployment is expected to present.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  // Serialized: these run against a single, non-scaled local Docker
  // Compose stack (one backend/worker/DB set), not a dedicated test
  // environment -- concurrent workers were observed to starve each
  // other under real load (Celery/DB contention) and produce flaky
  // 30s navigation timeouts that had nothing to do with the app itself.
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "https://localhost:8443",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
