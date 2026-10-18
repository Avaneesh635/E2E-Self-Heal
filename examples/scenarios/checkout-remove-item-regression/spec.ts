import { expect, test } from "@playwright/test";

test("removes the first cart item and updates the count", async ({ page }) => {
  await page.goto("/#/checkout");
  await page.click(".remove-item");
  await expect(page.locator("#cart-count")).toHaveText("1 item");
});
