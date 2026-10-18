import { expect, test } from "@playwright/test";

test("places the order when the button is clicked", async ({ page }) => {
  await page.goto("/#/checkout");
  await page.click("#place-order");
  await expect(page.locator("#order-status")).toHaveText("Order placed");
});
