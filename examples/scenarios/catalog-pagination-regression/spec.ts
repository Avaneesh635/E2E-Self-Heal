import { expect, test } from "@playwright/test";

test("advances to the second catalog page", async ({ page }) => {
  await page.goto("/#/catalog");
  await page.click("#catalog-next");
  await expect(page.locator("#catalog-page")).toHaveText("Page 2 of 2");
});
