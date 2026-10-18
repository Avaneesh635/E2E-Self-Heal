import { expect, test } from "@playwright/test";

test("signs the user out", async ({ page }) => {
  await page.goto("/#/account");
  await page.click("#sign-out");
  await expect(page.locator("#signed-out")).toHaveText("Signed out");
});
