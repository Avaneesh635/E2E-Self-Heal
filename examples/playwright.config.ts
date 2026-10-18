import { defineConfig } from "@playwright/test";

// Runs the scenario specs against the real React app. The webServer builds the Vite
// app and serves it via `vite preview`, so a change applied to a component (e.g.
// `git apply scenarios/id-rename/change.patch`) is reflected on the next test run.
// `E2E_DEMO_PORT` keeps two checkouts from sharing one preview server (and therefore
// one checkout's build).
const port = Number(process.env.E2E_DEMO_PORT ?? "4173");
const baseURL = `http://localhost:${port}`;

export default defineConfig({
  testDir: "./scenarios",
  testMatch: ["**/spec.ts", "**/*.spec.ts"],
  timeout: 30_000,
  expect: { timeout: 3_000 },
  use: {
    baseURL,
    actionTimeout: 3_000,
  },
  webServer: {
    command: "pnpm build && pnpm preview",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  reporter: [
    ["list"],
    [
      "../integrations/playwright-reporter/src/index.ts",
      { diffFile: "scenarios/classname-rename/change.patch" },
    ],
  ],
});
