import { expect, test } from "@playwright/test";

test("submits the form", async ({ page }) => {
  await page.goto("/");
  await page.click("form > button");
  await expect(page.getByText("Thanks!")).toBeVisible();
});
