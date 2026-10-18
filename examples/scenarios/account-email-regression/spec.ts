import { expect, test } from "@playwright/test";

test("saves the email address", async ({ page }) => {
  await page.goto("/#/account");
  await page.fill("#email-input", "grace@example.com");
  await page.click("#save-email");
  await expect(page.locator("#email-status")).toHaveText("Saved grace@example.com");
});
