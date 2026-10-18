import { expect, test } from "@playwright/test";

test("updates the subtotal when the quantity changes", async ({ page }) => {
  await page.goto("/#/checkout");
  await page.fill("#quantity", "3");
  await expect(page.locator("#subtotal")).toHaveText("$30.00");
});
