import { expect, test } from "@playwright/test";

test("asks to confirm deleting the account", async ({ page }) => {
  await page.goto("/#/settings");
  await page.click("#delete-account");
  await expect(page.getByText("Delete this account?")).toBeVisible();
});
