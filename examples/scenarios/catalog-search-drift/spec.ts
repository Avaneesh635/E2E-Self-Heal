import { expect, test } from "@playwright/test";

test("filters the catalog to the matching product", async ({ page }) => {
  await page.goto("/#/catalog");
  await page.fill("#catalog-search", "lamp");
  await expect(page.locator("#catalog-results").getByText("Desk Lamp")).toBeVisible();
  await expect(page.locator("#catalog-results").getByText("Wall Clock")).toBeHidden();
});
