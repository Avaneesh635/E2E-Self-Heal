import { expect, test } from "@playwright/test";

test("updates the password", async ({ page }) => {
  await page.goto("/#/account");
  await page.fill("#password-input", "correct-horse");
  await page.click("#save-password");
  await expect(page.locator("#password-status")).toHaveText("Password updated");
});
