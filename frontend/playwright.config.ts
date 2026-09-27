import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5174",
    channel: "chrome",
    headless: true,
    viewport: { width: 1440, height: 1100 },
  },
  webServer: [
    {
      command:
        "..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8100",
      url: "http://127.0.0.1:8100/health",
      env: {
        FIP_MARKET_DB: "../data/e2e-market.sqlite3",
        FIP_ARTIFACT_DIR: "../artifacts/e2e-freight",
        FIP_ANALYSIS_DB: "../data/e2e-analyses.sqlite3",
      },
      reuseExistingServer: false,
    },
    {
      command: "npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { FIP_API_TARGET: "http://127.0.0.1:8100" },
      reuseExistingServer: false,
    },
  ],
});
