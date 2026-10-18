import { expect, test } from "@playwright/test";

test("applies the SAVE5 coupon to the discount", async ({ page }) => {
  await page.goto("/#/checkout");
  await page.fill("#coupon-code", "SAVE5");
  await page.click("#apply-coupon");
  await expect(page.locator("#discount")).toHaveText("-$5.00");
});
