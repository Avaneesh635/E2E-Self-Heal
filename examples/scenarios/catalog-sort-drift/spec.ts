import { expect, test } from "@playwright/test";

test("sorts the catalog rows by price", async ({ page }) => {
  await page.goto("/#/catalog");
  await page.click(".catalog-sort");
  await expect(page.locator("#catalog-rows li").first()).toHaveText("Desk Lamp $20");
});
