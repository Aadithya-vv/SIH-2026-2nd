import { test, expect } from "@playwright/test";
test("trains probabilistic forecasts, inspects holdouts, and handles unavailable history", async ({
  page,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "05 Freight forecast", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Forecast series", exact: true }),
  ).toHaveValue("demo_panamax_index");
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/forecast/train") &&
      r.request().method() === "POST",
    { timeout: 120000 },
  );
  await page
    .getByRole("button", { name: "Train & evaluate", exact: true })
    .click();
  const trained = await response;
  expect(trained.status()).toBe(200);
  const output = await trained.json();
  expect(output.forecast_points).toHaveLength(4);
  for (const p of output.forecast_points) {
    expect(p.p10).toBeLessThanOrEqual(p.p50);
    expect(p.p50).toBeLessThanOrEqual(p.p90);
  }
  await expect(
    page.getByRole("heading", { name: "Forecast by horizon", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("SIMULATED DATA BACKTEST", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator(".recharts-area-area")).toBeVisible();
  await page.screenshot({
    path: "test-results/freight-forecast.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Out-of-sample backtest", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Out-of-sample backtest / final test",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".recharts-line-curve").first()).toBeVisible();
  await page
    .getByRole("combobox", { name: "Inspect horizon", exact: true })
    .selectOption("14");
  await expect(
    page.getByRole("heading", { name: "Model performance", exact: true }),
  ).toBeVisible();
  const body = {
    category: "FREIGHT",
    source_name: "Forecast browser short-history fixture",
    series_name: "Insufficient forecast history",
    csv_text:
      "date,value,known\n2026-08-01,12,2026-08-01T18:00:00Z\n2026-08-02,13,2026-08-02T18:00:00Z",
    date_column: "date",
    value_column: "value",
    available_at_column: "known",
    unit: "index_points",
    vessel_class: "PANAMAX",
  };
  const preview = await (
    await page.request.post("/api/data/import/csv", { data: body })
  ).json();
  await page.request.post("/api/data/import/csv", {
    data: { ...body, commit: true, preview_hash: preview.preview_hash },
  });
  await page.reload();
  await page
    .getByRole("button", { name: "05 Freight forecast", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Forecast series", exact: true })
    .selectOption({ label: "Insufficient forecast history" });
  await expect(
    page.getByText("Forecast unavailable.", { exact: false }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Train & evaluate", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("INSUFFICIENT_DATA");
  expect(errors).toEqual([]);
});
