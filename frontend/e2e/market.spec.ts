import { test, expect } from "@playwright/test";
test("market catalog, historical chart, CSV import and point-in-time feature export", async ({
  page,
}) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "04 Market intelligence", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Market history", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Historical series")).not.toBeEmpty({
    timeout: 15000,
  });
  await page.getByRole("button", { name: "Data catalog", exact: true }).click();
  await expect(
    page.getByText("COMMERCIAL_FEED_REQUIRED", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "DEMO_PARADIP_CONGESTION", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/market-catalog.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Import data", exact: true }).click();
  await page
    .getByLabel("Source name", { exact: true })
    .fill("Browser QA supplied records");
  await page
    .getByLabel("Series name", { exact: true })
    .fill("Browser QA freight history");
  await page
    .getByLabel("Publication column (optional)", { exact: true })
    .fill("known_at");
  await page.getByLabel("CSV file", { exact: true }).setInputFiles({
    name: "historical.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "date,value,known_at\n2026-08-01,1200,2026-08-01T18:00:00Z\n2026-08-02,1250,2026-08-02T18:00:00Z\n2026-08-03,-1,2026-08-03T18:00:00Z",
    ),
  });
  await page.getByRole("button", { name: "Validate CSV", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Validation preview", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("NEGATIVE_VALUE / STALE_DATA", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ingest validated rows", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Import saved", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "History", exact: true }).click();
  await page
    .getByLabel("Historical series")
    .selectOption({ label: "Browser QA freight history / IMPORTED" });
  await expect(
    page.getByText("USER_IMPORT", { exact: true }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Feature dataset", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Freight target", exact: true })
    .selectOption({ label: "Browser QA freight history" });
  await page
    .getByRole("button", { name: "Build feature dataset", exact: true })
    .click();
  await expect(
    page.getByText(
      "2 aligned rows / REVIEW_QUALITY_AND_PUBLICATION_ASSERTIONS",
      { exact: true },
    ),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download dataset + lineage (JSON)" })
    .click();
  expect((await download).suggestedFilename()).toBe("feature-dataset.json");
  await page.getByRole("button", { name: "History", exact: true }).click();
  await page
    .getByLabel("Historical series")
    .selectOption({ label: "DEMO_PANAMAX_INDEX / DEMO" });
  await expect(page.getByText("DEMO_ONLY", { exact: true })).toBeVisible();
  await expect(page.getByText("Loading history...", {exact:true})).toHaveCount(0);
  await expect(page.locator(".recharts-line-curve")).toBeVisible();
  await page.screenshot({
    path: "test-results/market-history.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
