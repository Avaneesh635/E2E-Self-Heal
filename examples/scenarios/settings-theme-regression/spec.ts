import { expect, test } from "@playwright/test";

test("applies the dark theme", async ({ page }) => {
  await page.goto("/#/settings");
  await page.selectOption("#theme-select", "dark");
  await expect(page.locator("#theme-indicator")).toHaveText("dark");
});
