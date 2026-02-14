import { defineConfig } from "@playwright/test";

/**
 * Playwright config optimized for recording demos.
 *
 * Usage: npx playwright test --config=playwright-demo.config.ts
 */
export default defineConfig({
  testDir: "./tests/playwright",
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on",
    video: {
      mode: "on",
      size: { width: 2560, height: 1440 }, // Record at 2K for supersampling
    },
    screenshot: "on",
    viewport: { width: 2560, height: 1440 }, // 2K viewport
    deviceScaleFactor: 1, // Standard DPI (viewport already large enough)
    // Slow down interactions for better visibility
    launchOptions: {
      slowMo: 500, // 500ms delay between actions
    },
  },
  webServer: {
    command: "npx http-server ./examples/sample-report -p 4173 -c-1",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    {
      name: "chromium-demo",
      use: {
        browserName: "chromium",
        viewport: { width: 2560, height: 1440 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
