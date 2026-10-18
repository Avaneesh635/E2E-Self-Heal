import { expect, test } from "@playwright/test";

test("turns email notifications on", async ({ page }) => {
  await page.goto("/#/settings");
  await page.click("#notifications-toggle");
  await expect(page.locator("#notifications-state")).toHaveText("On");
});
