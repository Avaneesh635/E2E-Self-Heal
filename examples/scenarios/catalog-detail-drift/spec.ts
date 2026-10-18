import { expect, test } from "@playwright/test";

test("reveals the product detail panel", async ({ page }) => {
  await page.goto("/#/catalog");
  await page.click(".catalog-detail");
  await expect(page.getByText("Desk Lamp: in stock")).toBeVisible();
});
