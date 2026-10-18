import { expect, test } from "@playwright/test";

test("saves the settings", async ({ page }) => {
  await page.goto("/#/settings");
  await page.click("#save-settings");
  await expect(page.locator("#save-status")).toHaveText("Saved");
});
