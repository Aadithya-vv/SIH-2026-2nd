import { test, expect } from "@playwright/test";
test("analyzes a shipment through the API and explains infeasibility", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Analyze voyage" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Analyze voyage" }).click();
  await expect(
    page.getByRole("heading", { name: "Recommended strategy" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open charter decision" }),
  ).toBeVisible();
  await expect(page.getByText("Inputs changed.", { exact: false })).toHaveCount(
    0,
  );
  await expect(
    page.locator("tbody tr").filter({ hasText: "Capesize" }),
  ).toContainText("FAIL");
  await page.screenshot({ path: "test-results/optimizer.png", fullPage: true });
  await page.getByRole("button", { name: "Why?" }).last().click();
  await expect(
    page.getByRole("heading", { name: "capesize / check results" }),
  ).toBeVisible();
  await expect(
    page
      .locator("tbody tr")
      .filter({ hasText: "Paradip" })
      .filter({ hasText: "DRAFT" }),
  ).toContainText("FAIL");
  await page.getByRole("button", { name: "01 Control center" }).click();
  await expect(
    page.getByRole("heading", { name: "Active demo shipment" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "02 Voyage optimizer" }).click();
  await page.getByLabel("Destination port").selectOption("Haldia");
  await expect(
    page.getByText("Inputs changed.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Analyze voyage" }).click();
  await expect(
    page.getByText("No feasible option", { exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
